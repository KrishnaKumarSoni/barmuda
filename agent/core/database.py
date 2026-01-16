import os
import asyncio
import threading
from google.cloud import firestore
from google.oauth2 import service_account
from datetime import datetime
from typing import Dict, Any, Literal, cast, List
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage

load_dotenv()

# --- Firestore Client Initialization ---
def get_db_client():
    """
    Returns an initialized Firestore AsyncClient using environment variables.
    """
    # Prefer the explicit path variable you use in .env
    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    
    # Fallback to standard Google var if set
    if not cred_path:
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if cred_path and os.path.exists(cred_path):
        # print(f"[DB] Initializing Firestore AsyncClient with {cred_path}")
        return firestore.AsyncClient.from_service_account_json(cred_path)
    else:
        # print("[DB] Initializing Firestore AsyncClient with default credentials")
        return firestore.AsyncClient()

def get_sync_db_client():
    """Returns a synchronous Firestore client for background threads."""
    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    if not cred_path:
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if cred_path and os.path.exists(cred_path):
        return firestore.Client.from_service_account_json(cred_path)
    else:
        return firestore.Client()

def get_utc_now() -> str:
    """Returns the current UTC time in ISO 8601 format with 'Z'."""
    return datetime.utcnow().isoformat() + "Z"

def _persist_new_session_sync(session_id: str, new_doc: Dict[str, Any]):
    """
    Background thread task to persist a new session document using sync client.
    Survives the closing of the async event loop.
    """
    try:
        # print(f"[DB] Persisting new session {session_id} in background thread...")
        db = get_sync_db_client()
        db.collection('sessions_v2').document(session_id).set(new_doc)
        # print(f"[DB] Successfully persisted session {session_id}")
    except Exception as e:
        print(f"[DB] Error persisting new session {session_id}: {e}")

async def init_session(session_id: str, form_id: str) -> Dict[str, Any]:
    """
    Creates a new session document in Firestore if it doesn't exist.
    Returns the full session data.
    """
    db = get_db_client()
    try:
        session_ref = db.collection('sessions_v2').document(session_id)
        session_doc = await session_ref.get()

        if session_doc.exists:
            # print(f"[DB] Session {session_id} found. Loading...")
            return cast(Dict[str, Any], session_doc.to_dict())
        
        # print(f"[DB] Creating new session for {session_id}...")
        
        new_doc = {
            "session_id": session_id,
            "form_id": form_id,
            "session_state": "ONGOING",
            "created_at": get_utc_now(),
            "last_updated": get_utc_now(),
            "messages": [],
            # responses map is strictly Key -> {value, status, timestamp}
            "responses": {} 
        }
        
        # Optimization: Use a thread for the write so we don't block 
        # and don't depend on the current event loop staying open.
        threading.Thread(target=_persist_new_session_sync, args=(session_id, new_doc)).start()
        
        return new_doc
    finally:
        db.close()

async def get_session_data(session_id: str) -> Dict[str, Any] | None:
    """
    Retrieves the session data from Firestore.
    """
    db = get_db_client()
    try:
        doc = await db.collection('sessions_v2').document(session_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    finally:
        db.close()

async def update_response_in_db(
    session_id: str, 
    question_key: str, 
    value: Any, 
    status: Literal["ANSWERED", "SKIPPED", "UNASKED"]
):
    """
    Updates a specific question's data in the 'responses' map in Firestore
    using dot notation for nested fields.
    """
    db = get_db_client()
    try:
        session_ref = db.collection('sessions_v2').document(session_id)
        
        # Use dot notation to update a field within the 'responses' map
        response_field_path = f'responses.{question_key}'
        
        await session_ref.update({
            response_field_path: {
                "value": value,
                "status": status,
                "timestamp": get_utc_now()
            },
            "last_updated": get_utc_now()
        })
    finally:
        db.close()

async def update_session_lifecycle(session_id: str, new_state: Literal["ONGOING", "FINISHED", "TERMINATED"]):
    """Updates the high-level status of the session in Firestore."""
    db = get_db_client()
    try:
        session_ref = db.collection('sessions_v2').document(session_id)
        await session_ref.update({
            "session_state": new_state,
            "last_updated": get_utc_now()
        })
    finally:
        db.close()

async def get_form_schema(form_id: str) -> Dict[str, Any] | None:
    """
    Retrieves the form schema from the 'form' collection in Firestore.
    """
    db = get_db_client()
    try:
        # print("--- [Database] Fetching form schema for form_id:", form_id)
        doc = await db.collection('forms_v2').document(form_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    finally:
        db.close()

async def save_session_messages(session_id: str, messages: List[BaseMessage]):
    """
    Updates the message history in the session document.
    """
    db = get_db_client()
    try:
        serialized_msgs = []
        for msg in messages:
            msg_data = {
                "type": msg.type,
                "content": msg.content,
                "timestamp": get_utc_now()
            }
            # Add additional metadata if available
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                 msg_data['tool_calls'] = msg.tool_calls
            
            serialized_msgs.append(msg_data)
            
        await db.collection('sessions_v2').document(session_id).update({
            "messages": serialized_msgs,
            "last_updated": get_utc_now()
        })
    except Exception as e:
        print(f"[DB] Error saving messages for {session_id}: {e}")
    finally:
        db.close()