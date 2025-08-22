"""
Background Data Extraction Service
Independent GPT-4o-mini powered extraction that runs asynchronously
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any
import queue

import firebase_admin
import openai
from dotenv import load_dotenv
from firebase_admin import firestore

from data_extraction import DataExtractionChain

load_dotenv()

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Firebase Admin SDK if not already initialized
def init_firebase():
    """Initialize Firebase Admin SDK if not already done"""
    global firestore_db
    
    if not firebase_admin._apps:
        # Check if running on Vercel/production with environment variables
        if os.environ.get("VERCEL") or os.environ.get("FIREBASE_PRIVATE_KEY"):
            # Production Firebase initialization
            service_account_info = {
                "type": "service_account",
                "project_id": os.environ.get("FIREBASE_PROJECT_ID", "barmuda-in"),
                "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace(
                    "\\n", "\n"
                ),
                "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('FIREBASE_CLIENT_EMAIL', '').replace('@', '%40')}",
            }
            
            cred = firebase_admin.credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://barmuda-in-default-rtdb.us-central1.firebasedatabase.app/'
            })
            print("Firebase Admin SDK initialized for production")
        else:
            # Local development - try to use service account key file
            try:
                cred = firebase_admin.credentials.Certificate("barmuda-in-firebase-adminsdk.json")
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://barmuda-in-default-rtdb.us-central1.firebasedatabase.app/'
                })
                print("Firebase Admin SDK initialized for development")
            except Exception as e:
                print(f"Warning: Could not initialize Firebase Admin SDK: {e}")
                return None
    
    try:
        firestore_db = firestore.client()
        return firestore_db
    except Exception as e:
        print(f"Warning: Could not get Firestore client: {e}")
        return None

# Initialize Firebase
firestore_db = init_firebase()

# Background extraction queue
extraction_queue = queue.Queue()
extraction_active = True

class BackgroundExtractor:
    """Handles background extraction of chat responses"""
    
    def __init__(self):
        self.extractor = DataExtractionChain()
        self.worker_thread = None
        self.start_worker()
    
    def start_worker(self):
        """Start the background worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            print("Background extraction worker started")
    
    def _worker_loop(self):
        """Main worker loop for processing extraction jobs"""
        global extraction_active
        
        while extraction_active:
            try:
                # Get extraction job from queue with timeout
                job = extraction_queue.get(timeout=5.0)
                
                if job is None:  # Shutdown signal
                    break
                
                session_id = job.get("session_id")
                trigger_reason = job.get("reason", "unknown")
                
                print(f"Processing background extraction for session {session_id} (reason: {trigger_reason})")
                
                # Perform the extraction
                result = self._extract_session_responses(session_id)
                
                if result.get("success"):
                    print(f"✅ Background extraction completed for session {session_id}")
                else:
                    print(f"❌ Background extraction failed for session {session_id}: {result.get('error')}")
                
                # Mark job as done
                extraction_queue.task_done()
                
            except queue.Empty:
                # No jobs in queue, continue waiting
                continue
            except Exception as e:
                print(f"Error in background extraction worker: {e}")
                time.sleep(1)  # Brief pause before retrying
    
    def queue_extraction(self, session_id: str, reason: str = "chat_ended"):
        """Queue a session for background extraction"""
        job = {
            "session_id": session_id,
            "reason": reason,
            "queued_at": datetime.now().isoformat()
        }
        
        try:
            # Add to queue (non-blocking)
            extraction_queue.put_nowait(job)
            print(f"Queued extraction for session {session_id} (reason: {reason})")
            return True
        except queue.Full:
            print(f"⚠️ Extraction queue is full, skipping session {session_id}")
            return False
    
    def _extract_session_responses(self, session_id: str) -> Dict[str, Any]:
        """Extract responses for a specific session"""
        try:
            global firestore_db
            if firestore_db is None:
                firestore_db = init_firebase()
            
            if firestore_db is None:
                return {"success": False, "error": "Firebase not initialized"}
            
            # Load session data
            session_doc = firestore_db.collection("chat_sessions").document(session_id).get()
            
            if not session_doc.exists:
                return {"success": False, "error": "Session not found"}
            
            session_data = session_doc.to_dict()
            
            # Check if extraction already exists
            existing_responses = firestore_db.collection("responses").where(
                "session_id", "==", session_id
            ).limit(1).get()
            
            if len(existing_responses) > 0:
                print(f"Responses already extracted for session {session_id}, skipping")
                return {"success": True, "message": "Already extracted"}
            
            # Perform extraction
            extraction_result = self.extractor.extract_responses(session_data)
            
            if extraction_result["success"]:
                # Prepare response data
                response_data = {
                    "session_id": session_id,
                    "form_id": session_data.get("form_id"),
                    "creator_id": session_data.get("form_data", {}).get("creator_id"),
                    "form_title": session_data.get("form_data", {}).get("title", "Untitled Form"),
                    "responses": extraction_result["extracted_responses"],
                    "metadata": {
                        **session_data.get("metadata", {}),
                        "chat_length": len(session_data.get("chat_history", [])),
                        **extraction_result["extraction_metadata"],
                        "device_id": session_data.get("metadata", {}).get("device_id"),
                        "location": session_data.get("metadata", {}).get("location", {}),
                        "extraction_type": "background_async",
                    },
                    "created_at": datetime.now(),
                    "partial": session_data.get("metadata", {}).get("partial", False),
                    "chat_transcript": session_data.get("chat_history", [])
                }
                
                # Save to responses collection
                doc_ref = firestore_db.collection("responses").add(response_data)
                
                # Update form stats
                self._update_form_stats(session_data)
                
                return {
                    "success": True,
                    "response_id": doc_ref[1].id,
                    "extracted_responses": len(extraction_result["extracted_responses"]),
                    "extraction_metadata": extraction_result["extraction_metadata"],
                }
            else:
                return extraction_result
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _update_form_stats(self, session_data: Dict):
        """Update form statistics after successful extraction"""
        try:
            form_id = session_data.get("form_id")
            if not form_id:
                return
            
            form_ref = firestore_db.collection("forms").document(form_id)
            
            # Get current stats for email notifications
            form_doc = form_ref.get()
            current_count = 0
            creator_email = None
            creator_name = None
            form_title = session_data.get("form_data", {}).get("title", "Untitled Form")
            
            if form_doc.exists:
                form_data = form_doc.to_dict()
                current_count = form_data.get("response_count", 0)
                creator_id = form_data.get("creator_id")
                
                # Get creator info for email
                if creator_id:
                    try:
                        creator_doc = firestore_db.collection("users").document(creator_id).get()
                        if creator_doc.exists:
                            creator_data = creator_doc.to_dict()
                            creator_email = creator_data.get("email")
                            creator_name = creator_data.get("name")
                    except Exception as e:
                        print(f"Could not get creator info for email: {str(e)}")
            
            # Update form stats
            new_count = current_count + 1
            form_ref.update({
                "response_count": firestore.Increment(1),
                "last_response": datetime.now(),
            })
            
            # Send email notifications for milestone responses
            if creator_email and new_count in [1, 5, 10]:
                try:
                    from email_service import email_service
                    email_result = email_service.send_response_alert(
                        creator_email, form_title, new_count, form_id, creator_name
                    )
                    if email_result.get("success"):
                        print(f"Response alert email sent to {creator_email} for response #{new_count}")
                    else:
                        print(f"Failed to send response alert email: {email_result.get('error')}")
                except Exception as e:
                    print(f"Error sending response alert email: {str(e)}")
                    
        except Exception as e:
            print(f"Error updating form stats: {e}")

# Global background extractor instance
background_extractor = None

def get_background_extractor():
    """Get or create the global background extractor"""
    global background_extractor
    if background_extractor is None:
        background_extractor = BackgroundExtractor()
    return background_extractor

def queue_extraction(session_id: str, reason: str = "chat_ended"):
    """Queue a session for background extraction"""
    extractor = get_background_extractor()
    return extractor.queue_extraction(session_id, reason)

def shutdown_background_extraction():
    """Shutdown the background extraction system"""
    global extraction_active, background_extractor
    
    print("Shutting down background extraction...")
    extraction_active = False
    
    # Send shutdown signal
    extraction_queue.put(None)
    
    if background_extractor and background_extractor.worker_thread:
        background_extractor.worker_thread.join(timeout=10)
    
    print("Background extraction shutdown complete")

# Auto-start on import
if __name__ != "__main__":
    get_background_extractor()