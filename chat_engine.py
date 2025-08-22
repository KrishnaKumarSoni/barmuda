"""
Barmuda Chat Agent - Simplified Agentic Chatbot (v3)
Uses OpenAI Agents SDK with minimal, focused tools
Tools return data only - agent handles all conversation
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import firebase_admin
import openai

# Debug import issue
try:
    from agents import Agent, Runner, function_tool
    print("SUCCESS: OpenAI Agents SDK imported", file=os.sys.stderr)
except ImportError as e:
    print(f"CRITICAL ERROR: Cannot import OpenAI Agents SDK: {e}", file=os.sys.stderr)
    # Create dummy classes to prevent complete failure
    class Agent:
        def __init__(self, *args, **kwargs):
            raise ImportError("OpenAI Agents SDK not available")
    class Runner:
        @staticmethod
        def run_sync(*args, **kwargs):
            raise ImportError("OpenAI Agents SDK not available")
    def function_tool(func):
        return func

from dotenv import load_dotenv
from firebase_admin import db, firestore

# Load environment variables and clean API key
load_dotenv()

# Critical: Strip the API key to prevent header errors
original_key = os.getenv("OPENAI_API_KEY", "")
clean_key = original_key.strip()
if original_key != clean_key:
    print(
        f"WARNING: Cleaned API key (removed {len(original_key) - len(clean_key)} characters)"
    )
    os.environ["OPENAI_API_KEY"] = clean_key

# Firebase should already be initialized by app.py when used via Flask
# For standalone usage, initialize if needed
if not firebase_admin._apps:
    # For production (Vercel), use environment variables
    # For local development, fall back to service account file
    if os.environ.get("VERCEL") or os.environ.get("FIREBASE_PRIVATE_KEY"):
        # Production environment - use environment variables
        firebase_config = {
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
            "universe_domain": "googleapis.com",
        }
        cred = firebase_admin.credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    else:
        # Local development - use service account file
        cred = firebase_admin.credentials.Certificate(
            "barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json"
        )
        firebase_admin.initialize_app(cred)

firestore_db = firestore.client()


@dataclass
class ChatSession:
    """Manages chat session state and context"""

    session_id: str
    form_id: str
    form_data: Dict
    responses: Dict = None
    current_question_index: int = 0
    chat_history: List = None
    metadata: Dict = None

    def __post_init__(self):
        if self.responses is None:
            self.responses = {}
        if self.chat_history is None:
            self.chat_history = []
        if self.metadata is None:
            self.metadata = {
                "start_time": datetime.now().isoformat(),
                "skip_count": 0,
                "redirect_count": 0,
                "partial": False,
                "ended": False,
            }


# Global session storage (in production, use Redis or similar)
active_sessions = {}


def load_session(session_id: str) -> ChatSession:
    """Load session from Firebase or memory with enhanced validation"""
    if session_id in active_sessions:
        return active_sessions[session_id]

    # Load from Firestore
    try:
        session_doc = firestore_db.collection("chat_sessions").document(session_id).get()

        if session_doc.exists:
            session_data = session_doc.to_dict()
            
            # Validate required fields
            required_fields = ["session_id", "form_id", "form_data"]
            for field in required_fields:
                if not session_data.get(field):
                    raise ValueError(f"Session missing required field: {field}")
            
            # Ensure form_data has questions
            if not isinstance(session_data.get("form_data"), dict) or not session_data["form_data"].get("questions"):
                raise ValueError("Session has invalid form_data structure")
            
            session = ChatSession(
                session_id=session_data["session_id"],
                form_id=session_data["form_id"],
                form_data=session_data["form_data"],
                responses=session_data.get("responses", {}),
                current_question_index=session_data.get("current_question_index", 0),
                chat_history=session_data.get("chat_history", []),
                metadata=session_data.get("metadata", {}),
            )
            active_sessions[session_id] = session
            return session
        else:
            raise ValueError(f"Session {session_id} not found")
            
    except Exception as e:
        # Clean up any corrupted session from memory
        if session_id in active_sessions:
            del active_sessions[session_id]
        raise ValueError(f"Failed to load session {session_id}: {str(e)}")


def save_session(session: ChatSession):
    """Save session to Firebase"""
    # Update in memory
    active_sessions[session.session_id] = session

    # Convert datetime objects to ISO strings for JSON serialization
    form_data_serialized = {}
    for key, value in session.form_data.items():
        if hasattr(value, "isoformat"):
            form_data_serialized[key] = value.isoformat()
        else:
            form_data_serialized[key] = value

    session_data = {
        "session_id": session.session_id,
        "form_id": session.form_id,
        "form_data": form_data_serialized,
        "responses": session.responses,
        "current_question_index": session.current_question_index,
        "chat_history": session.chat_history,
        "metadata": session.metadata,
        "last_updated": datetime.now().isoformat(),
    }

    # Save to Firestore
    firestore_db.collection("chat_sessions").document(session.session_id).set(
        session_data
    )

    # If session ended, also save to responses
    if session.metadata.get("ended", False):
        firestore_db.collection("chat_responses").document(session.session_id).set(
            session_data
        )


# ============================================================
# SIMPLIFIED TOOLS - Return data only, agent handles conversation
# ============================================================


@function_tool
def get_conversation_state(session_id: str) -> dict:
    """Get current conversation state and context"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])
        
        # Find current unanswered question - USE PERSISTENT INDEX
        current_question_index = session.metadata.get("current_question_index", 0)
        current_question = None
        
        # Ensure we stay on the correct question until properly answered
        for i in range(current_question_index, len(questions)):
            q = questions[i]
            if q.get("enabled", True) and str(i) not in session.responses:
                current_question = {
                    "question_number": i + 1,
                    "type": q["type"],
                    "index": i,
                    "has_options": bool(q.get("options", [])),
                    # NO raw text exposed - agent must use get_natural_question
                }
                # Update session to track current index
                session.metadata["current_question_index"] = i
                save_session(session)
                break
        
        # Calculate progress
        enabled_questions = [q for q in questions if q.get("enabled", True)]
        answered_count = len([r for r in session.responses.values() if r.get("value") != "[SKIP]"])
        
        return {
            "current_question": current_question,
            "progress": {
                "answered": answered_count,
                "total": len(enabled_questions),
                "skipped": session.metadata.get("skip_count", 0)
            },
            "conversation_state": {
                "message_count": len(session.chat_history),
                "redirect_count": session.metadata.get("redirect_count", 0),
                "session_ended": session.metadata.get("ended", False),
                "time_elapsed": _calculate_time_elapsed(session.metadata.get("start_time")),
                "pending_end_confirmation": session.metadata.get("pending_end_confirmation", False)
            },
            "recent_responses": _get_recent_responses(session, limit=3)
        }
    except Exception as e:
        return {"error": str(e)}


@function_tool
def save_user_response(session_id: str, response_text: str, question_index: int) -> dict:
    """Save user response for a specific question"""
    try:
        session = load_session(session_id)
        
        # Save response (NO RAW TEXT - for extraction later)
        session.responses[str(question_index)] = {
            "value": response_text,
            "timestamp": datetime.now().isoformat(),
            "question_index": question_index,
            "question_type": session.form_data["questions"][question_index]["type"]
        }
        
        save_session(session)
        
        return {
            "saved": True,
            "response_id": f"{session_id}_q{question_index}",
            "responses_count": len(session.responses)
        }
    except Exception as e:
        return {"saved": False, "error": str(e)}


@function_tool
def advance_to_next_question(session_id: str) -> dict:
    """Move to the next available question ONLY after current is answered"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])
        
        # Get current index from metadata
        current_index = session.metadata.get("current_question_index", 0)
        
        # Find next enabled, unanswered question
        next_question = None
        for i in range(current_index + 1, len(questions)):
            q = questions[i]
            if q.get("enabled", True) and str(i) not in session.responses:
                next_question = {
                    "type": q["type"],
                    "index": i,
                    "has_options": bool(q.get("options", [])),
                    "question_number": i + 1
                    # NO "text" or "options" fields - agent must ask naturally
                }
                # Update metadata to track new current question
                session.metadata["current_question_index"] = i
                break
        
        save_session(session)
        
        # Check if all questions completed
        enabled_questions = [q for q in questions if q.get("enabled", True)]
        answered_count = len([r for r in session.responses.values() if r.get("value") != "[SKIP]"])
        all_completed = answered_count >= len(enabled_questions)
        
        # Check for additional data collection (demographics & profile)
        demographics_enabled = []
        profile_data_enabled = []
        
        if all_completed:
            # Get enabled demographics
            demographics = session.form_data.get("demographics", {})
            demographics_enabled = [k for k, v in demographics.items() if v]
            
            # Get enabled profile data
            profile_data = session.form_data.get("profile_data", {})
            profile_data_enabled = [k for k, v in profile_data.items() if v]
        
        return {
            "advanced": True,
            "next_question": next_question,
            "all_questions_completed": all_completed,
            "demographics_enabled": demographics_enabled,
            "profile_data_enabled": profile_data_enabled,
            "progress": {
                "answered": answered_count,
                "total": len(enabled_questions)
            }
        }
    except Exception as e:
        return {"advanced": False, "error": str(e)}


@function_tool
def update_session_state(session_id: str, action: str, reason: str = "user_request") -> dict:
    """Update session state for skip, end, redirect tracking, etc."""
    try:
        session = load_session(session_id)
        
        if action == "skip":
            session.metadata["skip_count"] += 1
            current_idx = session.current_question_index
            session.responses[str(current_idx)] = {
                "value": "[SKIP]",
                "timestamp": datetime.now().isoformat(),
                "reason": reason
            }
            # Move to next question
            session.current_question_index += 1
            
        elif action == "end":
            # SAFETY CHECK: Only allow ending if confirmation was already requested
            if not session.metadata.get("pending_end_confirmation", False):
                return {
                    "action_completed": False,
                    "error": "Cannot end without confirmation. Use 'request_end_confirmation' first.",
                    "session_ended": False,
                    "requires_confirmation": True
                }
            
            # Proceed with ending
            session.metadata["ended"] = True
            session.metadata["end_time"] = datetime.now().isoformat()
            session.metadata["end_reason"] = reason
            session.metadata["pending_end_confirmation"] = False  # Clear pending state
            # Calculate if partial
            enabled_count = len([q for q in session.form_data.get("questions", []) if q.get("enabled", True)])
            answered_count = len([r for r in session.responses.values() if r.get("value") != "[SKIP]"])
            session.metadata["partial"] = answered_count < enabled_count * 0.8
            
            # Handle extraction based on environment
            # Vercel cannot run background threads, so we do synchronous extraction
            if os.environ.get("VERCEL"):
                # Synchronous extraction for Vercel/serverless
                try:
                    from data_extraction import DataExtractionChain
                    extractor = DataExtractionChain()
                    
                    # Load session for extraction
                    session_data = {
                        "session_id": session_id,
                        "form_id": session.form_id,
                        "form_data": session.form_data,
                        "responses": session.responses,
                        "chat_history": session.chat_history,
                        "metadata": session.metadata
                    }
                    
                    # Extract and save responses synchronously
                    result = extractor.save_extracted_responses(session_data)
                    if result.get("success"):
                        print(f"Synchronous extraction completed for session {session_id}")
                    else:
                        print(f"Synchronous extraction failed: {result.get('error')}")
                except Exception as e:
                    print(f"Error in synchronous extraction: {e}")
            else:
                # Background extraction for local development
                try:
                    from background_extraction import queue_extraction
                    queue_extraction(session_id, f"chat_ended_{reason}")
                    print(f"Queued background extraction for ended session {session_id}")
                except Exception as e:
                    print(f"Warning: Could not queue background extraction: {e}")
            
        elif action == "request_end_confirmation":
            # User wants to end but needs confirmation
            session.metadata["pending_end_confirmation"] = True
            session.metadata["end_request_time"] = datetime.now().isoformat()
            
        elif action == "redirect":
            session.metadata["redirect_count"] += 1
            
        elif action == "timeout":
            session.metadata["partial"] = True
            session.metadata["timeout"] = True
            
            # Handle extraction based on environment (same as above)
            if os.environ.get("VERCEL"):
                # Synchronous extraction for Vercel/serverless
                try:
                    from data_extraction import DataExtractionChain
                    extractor = DataExtractionChain()
                    
                    # Load session for extraction
                    session_data = {
                        "session_id": session_id,
                        "form_id": session.form_id,
                        "form_data": session.form_data,
                        "responses": session.responses,
                        "chat_history": session.chat_history,
                        "metadata": session.metadata
                    }
                    
                    # Extract and save responses synchronously
                    result = extractor.save_extracted_responses(session_data)
                    if result.get("success"):
                        print(f"Synchronous extraction completed for timeout session {session_id}")
                    else:
                        print(f"Synchronous extraction failed: {result.get('error')}")
                except Exception as e:
                    print(f"Error in synchronous extraction: {e}")
            else:
                # Background extraction for local development
                try:
                    from background_extraction import queue_extraction
                    queue_extraction(session_id, "timeout")
                    print(f"Queued background extraction for timeout session {session_id}")
                except Exception as e:
                    print(f"Warning: Could not queue background extraction: {e}")
            
        save_session(session)
        
        return {
            "action_completed": True,
            "action": action,
            "session_ended": session.metadata.get("ended", False),
            "redirect_count": session.metadata.get("redirect_count", 0),
            "pending_end_confirmation": session.metadata.get("pending_end_confirmation", False)
        }
    except Exception as e:
        return {"action_completed": False, "error": str(e)}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _calculate_time_elapsed(start_time_str: str) -> int:
    """Calculate seconds elapsed since start time"""
    if not start_time_str:
        return 0
    try:
        start_time = datetime.fromisoformat(start_time_str)
        return int((datetime.now() - start_time).total_seconds())
    except:
        return 0


def _get_recent_responses(session: ChatSession, limit: int = 3) -> List[Dict]:
    """Get recent responses for context"""
    recent = []
    for idx, response in sorted(session.responses.items(), key=lambda x: x[0])[-limit:]:
        if response.get("value") != "[SKIP]":
            recent.append({
                "question_index": idx,
                "value": response["value"],
                "timestamp": response.get("timestamp")
            })
    return recent


# ============================================================
# NEW INTELLIGENT TOOLS FOR PROMPT REFACTORING
# ============================================================

@function_tool
def validate_response(session_id: str, response: str, question_type: str, validation_type: str = None) -> dict:
    """Enhanced validation with human-like conversation guidance
    
    Args:
        session_id: Current session ID
        response: User's response text
        question_type: text/multiple_choice/yes_no/rating/number
        validation_type: Optional - email/phone/linkedin/website/nonsense/vague
    
    Returns validation result with contextual, natural follow-up suggestions
    """
    import re
    
    try:
        session = get_session(session_id)
        if not session:
            return {"valid": False, "error": "Session not found"}
        
        # Get conversation context for personalized responses
        chat_history = session.chat_history[-3:] if session.chat_history else []
        user_name = None
        previous_responses = []
        
        # Extract user name and previous context from chat history
        for message in session.chat_history:
            if message.get("role") == "user":
                content = message.get("content", "").strip()
                # Simple name detection from early responses
                if len(content.split()) <= 3 and any(char.isalpha() for char in content):
                    if not user_name and len(content) < 30:
                        potential_name = content.split()[0]
                        if potential_name.lower() not in ['yes', 'no', 'maybe', 'sure', 'ok', 'okay']:
                            user_name = potential_name
                previous_responses.append(content)
        
        # Normalize response for analysis
        response_clean = response.strip()
        response_lower = response.strip().lower()
        
        # Enhanced nonsense detection with context awareness
        nonsense_patterns = [
            r'^[0-9]+$',  # Just numbers for non-number questions
            r'^(ola|bhoot|ringa|la+|ha+|lol|lmao|rofl|omg|wtf|idk).*',  # Common nonsense
            r'^[^a-zA-Z0-9\s]{3,}$',  # Special chars only
            r'^(.)\1{4,}',  # Repeated chars (aaaaa, !!!!!!)
            r'^(asdf|qwerty|zxcv|test|hello world).*',  # Keyboard mashing
        ]
        
        # Creative nonsense indicators with context
        creative_nonsense_indicators = [
            'bananas', 'purple elephants', 'flying unicorns', 'rainbow dragons', 'aliens',
            'moon cheese', 'chocolate rain', 'dancing penguins', 'singing cats', 'magic wizard',
            'pokemon battle', 'superhero cape', 'batman signal', 'superman flying', 'fairy dust'
        ]
        
        # Check if response contains multiple unrelated concepts (likely nonsense)
        response_words = response.lower().split()
        nonsense_word_count = sum(1 for word in response_words if word in creative_nonsense_indicators)
        
        # If response has 2+ nonsense indicators for serious questions, it's likely nonsense
        if (nonsense_word_count >= 2 and question_type in ['multiple_choice', 'rating', 'yes_no'] and 
            len(response_words) <= 6):  # Short responses with multiple nonsense words
            return {
                "valid": False,
                "reason": "creative_nonsense",
                "suggestion": "I need a real answer here. Can you give me a serious response?",
                "confidence": 0.9
            }
        
        if question_type not in ['number', 'rating'] and validation_type != 'email':
            for pattern in nonsense_patterns:
                if re.match(pattern, response):
                    return {
                        "valid": False,
                        "reason": "nonsense",
                        "suggestion": "I need a real answer here. Can you give me an actual response?",
                        "confidence": 0.9
                    }
        
        # Check for vague responses
        vague_responses = ['meh', 'idk', 'dunno', 'whatever', 'nothing', 'none', 'idc', 'maybe', 'perhaps']
        if response in vague_responses:
            return {
                "valid": False,
                "reason": "vague",
                "suggestion": "Can you be more specific? Even a rough idea would help!",
                "confidence": 0.8
            }
        
        # Validation by type
        if validation_type == 'email':
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, response):
                return {"valid": True, "cleaned_value": response, "confidence": 1.0}
            return {
                "valid": False,
                "reason": "invalid_email",
                "suggestion": "Could you share that as an email address? (like user@domain.com)",
                "confidence": 0.9
            }
            
        elif validation_type == 'phone':
            # Remove common separators
            cleaned = re.sub(r'[\s\-\(\)\+\.]', '', response)
            if re.match(r'^[0-9]{10,15}$', cleaned):
                return {"valid": True, "cleaned_value": cleaned, "confidence": 1.0}
            return {
                "valid": False,
                "reason": "invalid_phone",
                "suggestion": "What's your phone number? (10-15 digits)",
                "confidence": 0.9
            }
            
        elif validation_type == 'linkedin':
            if 'linkedin.com/in/' in response or re.match(r'^[a-zA-Z0-9\-]+$', response):
                return {"valid": True, "cleaned_value": response, "confidence": 1.0}
            return {
                "valid": False,
                "reason": "invalid_linkedin",
                "suggestion": "What's your LinkedIn profile URL or username?",
                "confidence": 0.8
            }
            
        elif validation_type == 'website':
            url_pattern = r'^(https?://)?([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}.*$'
            if re.match(url_pattern, response):
                return {"valid": True, "cleaned_value": response, "confidence": 1.0}
            return {
                "valid": False,
                "reason": "invalid_website",
                "suggestion": "What's your website URL?",
                "confidence": 0.8
            }
            
        elif question_type == 'rating':
            if response in ['1', '2', '3', '4', '5']:
                return {"valid": True, "cleaned_value": response, "confidence": 1.0}
            # Try to extract number from text
            numbers = re.findall(r'\b[1-5]\b', response)
            if numbers:
                return {"valid": True, "cleaned_value": numbers[0], "confidence": 0.8}
            return {
                "valid": False,
                "reason": "invalid_rating",
                "suggestion": "How would you rate that from 1 to 5?",
                "confidence": 0.9
            }
            
        elif question_type == 'yes_no':
            yes_patterns = ['yes', 'yeah', 'yep', 'sure', 'definitely', 'absolutely', 'correct', 'right', 'true', 'y']
            no_patterns = ['no', 'nope', 'nah', 'negative', 'false', 'wrong', 'incorrect', 'n']
            
            if any(pattern in response for pattern in yes_patterns):
                return {"valid": True, "cleaned_value": "yes", "confidence": 0.9}
            elif any(pattern in response for pattern in no_patterns):
                return {"valid": True, "cleaned_value": "no", "confidence": 0.9}
            return {
                "valid": False,
                "reason": "unclear_yes_no",
                "suggestion": "Is that a yes or no?",
                "confidence": 0.7
            }
            
        elif question_type == 'number':
            numbers = re.findall(r'\b\d+\b', response)
            if numbers:
                return {"valid": True, "cleaned_value": numbers[0], "confidence": 0.9}
            return {
                "valid": False,
                "reason": "no_number",
                "suggestion": "Can you give me a number?",
                "confidence": 0.8
            }
        
        # ENHANCED: Default validation with human-like suggestions for text questions
        if question_type == 'text':
            # Check for extremely short responses that might need elaboration
            if len(response_clean) <= 2 and response_clean.lower() not in ['me', 'hi', 'ok', 'no', 'na', 'nm']:
                name_part = f" {user_name}" if user_name else ""
                return {
                    "valid": False,
                    "reason": "too_short",
                    "suggestion": f"Can you tell me a bit more about that{name_part}? 😊",
                    "confidence": 0.6
                }
            
            # Check for responses that seem dismissive but could be expanded
            dismissive_patterns = ['fine', 'okay', 'ok', 'good', 'bad', 'nice', 'cool', 'meh']
            if response_lower in dismissive_patterns and len(previous_responses) > 2:
                return {
                    "valid": False,
                    "reason": "needs_elaboration", 
                    "suggestion": f"That's helpful! What specifically made it {response_lower} for you?",
                    "confidence": 0.7
                }
        
        # Multiple choice questions - accept anything but suggest if unclear
        elif question_type == 'multiple_choice':
            # If response seems like they're trying to answer but unclear
            if len(response_clean) > 1 and 'option' not in response_lower:
                return {
                    "valid": True,
                    "cleaned_value": response_clean,
                    "confidence": 0.8,
                    "note": "free_response_to_multiple_choice"
                }
        
        # Default for other text questions - almost always valid unless nonsense
        return {
            "valid": True, 
            "cleaned_value": response_clean, 
            "confidence": 0.85,
            "context": {
                "user_name": user_name,
                "response_count": len(previous_responses)
            }
        }
        
    except Exception as e:
        return {"valid": True, "error": str(e), "confidence": 0.5}


@function_tool
def check_content_sensitivity(text: str) -> dict:
    """Detect concerning or emotional content and suggest appropriate responses
    
    Args:
        text: User's message to analyze
    
    Returns sensitivity analysis with suggested acknowledgment
    """
    try:
        text_lower = text.lower()
        
        # Concerning content patterns
        concerning_keywords = [
            'suicide', 'kill myself', 'end my life', 'death', 'dying', 'dead',
            'bomb', 'bombing', 'explosion', 'violence', 'murder', 'killing',
            'gun', 'weapon', 'shoot', 'attack', 'terrorism', 'harm', 'hurt',
            'self-harm', 'cutting', 'bleeding', 'overdose'
        ]
        
        # Emotional content patterns
        emotional_keywords = [
            'angry', 'frustrated', 'sad', 'depressed', 'anxious', 'scared',
            'hate', 'upset', 'crying', 'miserable', 'lonely', 'hopeless',
            'stressed', 'overwhelmed', 'disappointed', 'heartbroken'
        ]
        
        # Check for concerning content
        for keyword in concerning_keywords:
            if keyword in text_lower:
                return {
                    "severity": "concerning",
                    "category": "serious_content",
                    "suggested_response": "That's really heavy. I hear you.",
                    "requires_acknowledgment": True,
                    "never_say": ["No worries!", "Cool!", "Thanks for sharing!", "Got it!", "Interesting!"],
                    "confidence": 0.95
                }
        
        # Check for emotional content
        for keyword in emotional_keywords:
            if keyword in text_lower:
                return {
                    "severity": "emotional",
                    "category": "feelings",
                    "suggested_response": "That sounds really tough.",
                    "requires_acknowledgment": True,
                    "never_say": ["Got it!", "Cool!", "No worries!"],
                    "confidence": 0.85
                }
        
        # Normal content
        return {
            "severity": "normal",
            "category": "standard",
            "suggested_response": None,
            "requires_acknowledgment": False,
            "confidence": 0.9
        }
        
    except Exception as e:
        return {
            "severity": "normal",
            "category": "error",
            "error": str(e),
            "confidence": 0.5
        }


def get_cached_natural_question(session_id: str, question_index: int) -> dict:
    """Get cached natural question for consistency across conversation"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])
        
        if question_index >= len(questions):
            return {"error": "Question index out of range"}
        
        current_q = questions[question_index]
        cache_key = f"natural_q_{question_index}"
        
        # Check if we have cached natural question
        if cache_key in session.metadata:
            return session.metadata[cache_key]
        
        # Generate and cache natural question
        natural_data = _get_natural_question_data(
            session_id, 
            current_q.get("text", ""), 
            current_q.get("type", "text"),
            question_index
        )
        
        # Cache for consistency
        session.metadata[cache_key] = natural_data
        save_session(session)
        
        return natural_data
        
    except Exception as e:
        return {"error": str(e)}

def _get_natural_question_data(session_id: str, question_text: str, question_type: str, question_index: int) -> dict:
    """Helper function to get natural question data (used both by tool and chip extraction)"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])
        current_q = questions[question_index] if question_index < len(questions) else {}
        
        # Common conversational starters
        starters = ["Hey!", "So,", "Alright,", "Cool,", "Nice,", "Great,"]
        starter = starters[question_index % len(starters)] if question_index > 0 else "Hey!"
        
        # Transform based on type
        text_lower = question_text.lower()
        
        # Natural transformations
        transformations = {
            # Demographics
            "what is your age": f"{starter} How old are you?",
            "age": "How old are you?",
            "what's your age": "How old are you?",
            "gender": "What's your gender?",
            "location": "Where are you from?",
            "occupation": "What do you do for work?",
            
            # Common patterns
            "how satisfied": "How satisfied are you with this?",
            "rate your": "How would you rate this?",
            "do you": f"{starter} Do you",
            "are you": f"{starter} Are you",
            "what is your": f"{starter} What's your",
            "tell us about": f"{starter} Tell me about",
            "describe": f"{starter} Can you describe",
            "how often": f"{starter} How often do you",
            "how many": f"{starter} How many",
        }
        
        # Find matching transformation
        natural_question = None
        for pattern, replacement in transformations.items():
            if pattern in text_lower:
                natural_question = text_lower.replace(pattern, replacement)
                break
        
        if not natural_question:
            # Default transformations by type
            if question_type == "yes_no":
                natural_question = f"{starter} {question_text}" if not question_text.startswith(("Do", "Are", "Is", "Can", "Would")) else question_text
            elif question_type == "rating":
                natural_question = f"How would you rate {question_text.lower().replace('rate', '').strip()}?"
            elif question_type == "multiple_choice":
                natural_question = f"{starter} {question_text.rstrip('?')}?"
            else:
                natural_question = f"{starter} {question_text}"
        
        # Prepare UI options for chips
        ui_options = []
        show_chips = False
        
        if question_type == "yes_no":
            ui_options = ["Yes", "No"]
            show_chips = True
        elif question_type == "rating":
            ui_options = ["1", "2", "3", "4", "5"]
            show_chips = True
        elif question_type == "multiple_choice" and current_q.get("options"):
            ui_options = current_q["options"][:5]  # Limit to 5 for UI
            show_chips = True
        
        # Add follow-up prompts
        follow_ups = [
            "Tell me more about that",
            "Why's that?",
            "Can you elaborate?",
            "What makes you say that?",
            "Interesting, why?"
        ]
        
        return {
            "natural_question": natural_question.capitalize(),
            "show_chips": show_chips,
            "chip_options": ui_options,
            "chip_type": question_type if show_chips else None,
            "follow_up_prompts": follow_ups[:2],
            "question_index": question_index,
            "original_text": question_text
        }
        
    except Exception as e:
        # Fallback to original question
        return {
            "natural_question": question_text,
            "show_chips": False,
            "chip_options": [],
            "error": str(e)
        }


@function_tool
def get_current_question_naturally(session_id: str) -> dict:
    """Get the current question to ask naturally with consistency"""
    try:
        session = load_session(session_id)
        current_index = session.metadata.get("current_question_index", 0)
        
        return get_cached_natural_question(session_id, current_index)
        
    except Exception as e:
        return {"error": str(e)}

@function_tool
def get_natural_question(session_id: str, question_text: str, question_type: str, question_index: int) -> dict:
    """Transform formal questions into natural conversation with optional UI hints
    
    Args:
        session_id: Current session ID
        question_text: Original question text
        question_type: text/multiple_choice/yes_no/rating/number
        question_index: Current question number
    
    Returns natural phrasing and UI options for chips
    """
    return _get_natural_question_data(session_id, question_text, question_type, question_index)


# ============================================================
# MAIN CHAT AGENT CLASS
# ============================================================

class FormChatAgent:
    """Simplified chat agent using OpenAI Agents SDK"""

    def __init__(self, openai_api_key: str):
        # Strip whitespace from API key to prevent header errors
        self.openai_api_key = (
            openai_api_key.strip() if openai_api_key else openai_api_key
        )
        # Set the API key in the environment for OpenAI Agents SDK
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        openai.api_key = self.openai_api_key
        
        # Disable OpenAI telemetry to avoid traces/ingest errors
        os.environ["OPENAI_DISABLE_TELEMETRY"] = "true"
        os.environ["OPENAI_LOG_LEVEL"] = "error"  # Reduce logging noise
        
        # Try to disable httpx INFO logging which shows the traces calls
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)

        # Ensure event loop exists for async operations
        import asyncio

        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Create agent with simplified tools
        self.agent = Agent(
            name="Barney",
            model="gpt-4o-mini",
            instructions=self._get_system_instructions(),
            tools=[
                get_conversation_state,
                get_current_question_naturally,
                save_user_response,
                advance_to_next_question,
                update_session_state,
                validate_response,
                check_content_sensitivity,
                get_natural_question
            ],
        )

    def _get_system_instructions_v2(self) -> str:
        """Enhanced system instructions for human-like conversation"""
        return """You are Barney, a friendly survey assistant who conducts conversations like a skilled human interviewer.

🎯 YOUR MISSION: Create natural, flowing conversations that feel genuinely human - not robotic or repetitive.

🚨 MANDATORY: You MUST use tools for EVERY action. Never act without calling tools first.

# HUMAN-LIKE CONVERSATION PRINCIPLES

## 1. INTELLIGENT QUESTION TRANSITIONS
- ANALYZE user's response quality before deciding next action
- If response covers multiple aspects: Extract what you can, only follow up on gaps
- If response is rich and complete: Move forward naturally
- If response is vague or incomplete: Ask ONE specific follow-up
- NEVER repeat the same question - rephrase or approach differently

## 2. CONTEXTUAL ACKNOWLEDGMENT (Not Generic Responses)
- Reference SPECIFIC details from their response
- Show you're actively listening and processing
- Examples:
  ✅ "That inconsistency between the first and second agent sounds frustrating"
  ✅ "I can see why that mixed experience would make you hesitant to recommend"
  ❌ "Got it! 😊" (generic, robotic)
  ❌ "Thanks for sharing!" (generic, robotic)

## 3. NATURAL CONVERSATION ENDINGS
- DETECT completion signals: "that's all", "I'm done", "nothing else"
- RECOGNIZE when sufficient information is gathered
- End gracefully: "That's really helpful feedback! I think I've got everything I need. Thanks for taking the time! 😊"
- AVOID: "Do you want to finish the survey?" (robotic)

# REQUIRED WORKFLOW:

## STEP 1: CONVERSATION START
1. CALL get_conversation_state(session_id)
2. CALL get_current_question_naturally(session_id)
3. Use natural_question from tool - be conversational

## STEP 2: WHEN USER RESPONDS
1. CALL check_content_sensitivity(user_response) first
2. CALL validate_response(session_id, response, question_type)
3. ANALYZE the validation result:
   - If valid=true AND response is complete: SAVE → ADVANCE → Acknowledge specifically
   - If valid=true BUT response seems incomplete: Acknowledge → Ask ONE clarifying question
   - If valid=false: Use tool suggestion with empathy
4. CRAFT HUMAN-LIKE ACKNOWLEDGMENT based on content

# ENHANCED RESPONSE PATTERNS:

## Smart Acknowledgments:
- For detailed responses: "That's really insightful - especially about [specific detail]"
- For mixed feelings: "I hear the frustration about X, but sounds like Y worked well"
- For strong opinions: "That's clear feedback - no ambiguity there!"
- For hesitation: "I can understand the uncertainty given that experience"

## Intelligent Follow-ups:
- For partial answers: "That's helpful! What about [specific missing aspect]?"
- For stories: "Interesting! How did that make you feel about [topic]?"
- For vague responses: "Could you help me understand what you mean by [their words]?"

## Natural Transitions:
- "That makes sense given what you shared..."
- "Speaking of [their topic], I'm curious about..."
- "That reminds me to ask about..."
- "Building on that experience..."

# CONVERSATION QUALITY RULES:

✅ DO:
- Reference their specific words and experiences
- Show genuine curiosity about their perspective
- Adapt your tone to match their communication style
- Use their language/terminology back to them
- Recognize when they've fully answered and move on

❌ NEVER:
- Use generic acknowledgments repeatedly
- Ask the same question twice in different words
- Ignore rich context they've provided
- Force completion when they signal they're done
- Reveal multiple choice options in your response

# TOOLS ARE MANDATORY:
- get_conversation_state() before every interaction
- check_content_sensitivity() for all user input
- validate_response() before saving anything
- save_user_response() only when response is complete and valid
- advance_to_next_question() only after successful save

🎯 SUCCESS METRIC: User should feel like they just had a thoughtful conversation with a human who was genuinely interested in their perspective.

You MUST call tools before every action. No exceptions. Create conversations that flow naturally."""

    def _get_system_instructions(self) -> str:
        """Get system instructions for the agent"""
        # Toggle between old (175 lines) and new (40 lines) prompt versions
        USE_SIMPLIFIED_PROMPT = True  # Set to True to activate new system
        
        if USE_SIMPLIFIED_PROMPT:
            return self._get_system_instructions_v2()
        
        # Original prompt (keeping for safety/rollback)
        return """# YOUR OBJECTIVE
🎯 Your goal is to collect HIGH-QUALITY, MEANINGFUL responses for all survey questions. Quality matters more than speed. Don't accept nonsense or off-topic answers - probe for real insights.

# IDENTITY
You are Barney. Be casual, friendly, and direct. Keep responses under 20 words. Ask one clear question at a time.

# CRITICAL SAFETY & SENSITIVITY RULES
🚨 PRIORITY #1: Handle sensitive content appropriately:

## CONCERNING CONTENT (death, suicide, self-harm, violence, bombs, bombing, killing, hate, murder, gun, weapon):
- MANDATORY: ALWAYS acknowledge seriousness FIRST: "That's really heavy" / "That sounds really difficult" / "That's concerning"
- ABSOLUTELY NEVER say "No worries", "Cool", "Thanks for sharing", "Got it!" or "Interesting" 
- NEVER use happy emojis (😊) or dismissive language with concerning content
- Show genuine concern without being preachy
- After acknowledging seriousness, gently continue: "I hear you. [next question]"
- If uncertain whether content is concerning, err on the side of treating it seriously

## EMOTIONAL CONTENT (anger, frustration, sadness):
- Validate feelings: "That sounds frustrating" / "I can understand why that's tough"
- NEVER dismiss or minimize: No "Got it!" for serious emotions

## ABSOLUTELY FORBIDDEN RESPONSES TO CONCERNING CONTENT:
❌ NEVER EVER: "No worries!" to bombs/violence/death/harm
❌ NEVER EVER: "Thanks for sharing" to death/violence/harm  
❌ NEVER EVER: "Cool" or "Awesome" to negative/concerning content
❌ NEVER EVER: Happy emojis (😊 🙂 😄) with concerning content
❌ NEVER EVER: "Interesting" to concerning statements
❌ NEVER EVER: "Got it!" to concerning/emotional content
❌ NEVER EVER: Dismissive phrases like "Let's move on" without acknowledgment first

✅ APPROPRIATE: 
- For concerning: "That's really heavy. [gentle transition to next]"
- For emotional: "I hear that's frustrating. [next question]"
- For normal: "Makes sense!" / "I see!"

# CRITICAL ANTI-BIAS RULE
🚨 NEVER reveal options, scales, or structured choices. Always ask open-ended questions.
❌ "Rate 1-5" / "Choose A/B" / "Here's the next question"
✅ "How satisfied are you?" / Natural transitions only

FORBIDDEN: 
- "next question", "here it is", "question #X"
- Over-explaining what you're doing
- "I see we're kicking off with...", "I'm interested in understanding..."
- Long philosophical responses

REQUIRED: Context-appropriate acknowledgments based on content sensitivity

# TOOLS AVAILABLE
1. get_conversation_state(session_id) - Check what question you're on, progress, and survey status
2. save_user_response(session_id, response, question_index) - Record user's answer
3. advance_to_next_question(session_id) - Move to next question
4. update_session_state(session_id, action, reason) - Handle skip/end/redirect

🎯 MANDATORY: Start every conversation by calling get_conversation_state() to understand current progress.
🚨 CRITICAL: When you see question text in tool results, NEVER ask it verbatim. Transform it naturally based on the type and topic.

# QUESTION TRANSFORMATION BY TYPE
- text: "Tell me about..." / "What's..."
- multiple_choice: Ask openly, ignore options  
- yes_no: "Do you..." / "Are you..."
- rating: "How satisfied..."
- number: "How many..." 

GOOD EXAMPLES:
"Hey! How old are you?"
"Nice. What's your gender?"  
"Cool. How often do you shop?"

BAD EXAMPLES (DON'T DO THIS):
❌ "Great to have you back! I see we're kicking off with the first question about age range..."
❌ "I'm interested in understanding your age perspective, so could you share your thoughts on that?"
❌ "Speaking of age, how would you describe your current living situation?"

Be DIRECT. No meta-commentary. No over-explaining. Just ask what you need to know.

# RESPONSE HANDLING

## Standard Flow
1. VALIDATE response is relevant to question (not nonsense/off-topic)
2. If INVALID: Probe for real answer (up to 3 times)
3. If VALID: Acknowledge appropriately based on content sensitivity
4. save_user_response() ONLY if valid or after 3 failed attempts
5. advance_to_next_question()
6. Ask next conversationally

## Special Cases

### DATA QUALITY VALIDATION (CRITICAL!)
**Nonsense/Off-topic Answers** (e.g., "ola ola", "908" for non-number questions, song lyrics, random words):
- DO NOT ACCEPT as valid responses
- Probe up to 3 times: "I need a real answer here. [rephrase question]"
- After 3rd attempt, mark as [INVALID] and move on
- Examples of nonsense: "bhoot", "who let the dogs out", "ringa ringa roses", random numbers for text questions

**Vague Answers** ("meh", "idk", "whatever"):
- Probe twice: "Can you be more specific?" → "Even a rough idea would help"
- After 2nd probe, accept if still vague

**Valid Off-topic** (legitimate but misplaced):
- Save for later: "Great point! I'll note that for later"

**Skip request**: "No worries! 😊" → update_session_state("skip") → advance
**Multi-answers**: Save current only, "I'll ask about other stuff later"
**Concerning/Sensitive Content**: Follow SAFETY RULES above - acknowledge seriousness first

## Probing Techniques
- Echo: "Confusing how?"  
- Tell-me-more: "Can you paint me a picture?"
- Example: "Can you think of a specific time?"
- Why ladder: "What led to that?" / "What's important about that?"

# COLLECTING ADDITIONAL DATA (DEMOGRAPHICS & PROFILE)
**IMPORTANT**: After all main survey questions are completed, check for additional data collection:

**Check Required**: Use advance_to_next_question() to see if all_questions_completed = True
**If Yes**: Check the session's form_data for enabled "demographics" and "profile_data" fields
**Collection Flow**:
1. If demographics enabled: "Great! Just a few quick demographic questions: [list enabled fields]"
2. Collect each enabled demographic field naturally in conversation
3. If profile_data enabled: "And lastly, some profile information: [list enabled fields]"
4. For profile fields with validation (email, phone, linkedin, website): Ask politely for correct format if needed
5. Store all additional responses using save_user_response()

**Validation Examples**:
- Email: "Could you share that as an email address? (like user@domain.com)"
- Phone: "What's your phone number?"
- LinkedIn: "What's your LinkedIn profile URL?"
- Website: "What's your website URL?"

**After All Data Collected**: Proceed to normal ending conversation flow

# ENDING CONVERSATIONS
**CRITICAL: Two-step confirmation required**

Step 1 - First end request:
→ update_session_state("request_end_confirmation")
→ "Are you sure? You've shared great insights on X of Y topics"

Step 2 - Any confirmation ("yes"/"sure"/"END MAN"):
→ IMMEDIATELY update_session_state("end", "user_confirmed")
→ "Thanks for your time! 👋"

Never call update_session_state("end") without prior confirmation request.

# RESUMING SESSIONS
ALWAYS respond to their actual message first. Never generic "welcome back".

# CONVERSATION PSYCHOLOGY
- Match their energy/style
- Show genuine interest: "That's fascinating!"
- One question at a time
- Use inclusive language
- Allow thoughtful pauses

# CONTEXT-RELATED QUESTIONS 
🎯 **IMPORTANT**: If user asks about the bot, organization, survey purpose, or anything related to the Bot Context:
1. Answer naturally using the Bot Context information (if provided)
2. Keep response brief and helpful (under 20 words)
3. **DO NOT** save_user_response() or advance_to_next_question() 
4. Smoothly redirect back to current survey question
5. Example: "I'm Sarah from marketing! We're studying customer satisfaction. So about your shopping habits..."

**Context Question Examples**:
- "Who are you?" / "What's this for?" / "Why are you asking?"
- "What company is this?" / "Who's running this survey?"
- Questions about the organization, purpose, or background

**Key**: Answer from Bot Context, then redirect to survey naturally.

# QUALITY MARKERS
Good: ✅ Stories, emotional language, elaboration
Probe: ⚠️ All positive/negative, very short, rushing

Be human, not a data collector."""


    def create_session(
        self, form_id: str, device_id: str = None, location: Dict = None
    ) -> str:
        """Create a new chat session"""
        try:
            # Get form data
            form_doc = firestore_db.collection("forms").document(form_id).get()
            if not form_doc.exists:
                raise ValueError(f"Form {form_id} not found")

            form_data = form_doc.to_dict()

            # Generate session ID
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

            # Create session
            session = ChatSession(
                session_id=session_id,
                form_id=form_id,
                form_data=form_data,
                metadata={
                    "start_time": datetime.now().isoformat(),
                    "device_id": device_id,
                    "location": location,
                    "skip_count": 0,
                    "redirect_count": 0,
                    "partial": False,
                    "ended": False,
                },
            )

            save_session(session)
            return session_id

        except Exception as e:
            import traceback
            print(f"SESSION CREATION ERROR: {str(e)}")
            print(f"TRACEBACK: {traceback.format_exc()}")
            raise Exception(f"Failed to create session: {str(e)}")

    def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Process a user message and return agent response"""
        try:
            session = load_session(session_id)
            
            # Enhanced session validation
            if session.metadata.get("ended", False):
                return {
                    "success": False,
                    "response": "This conversation has already ended. Thanks for your participation!",
                    "error": "session_ended"
                }
            
            # Check for session timeout (24 hours max)
            start_time_str = session.metadata.get("start_time")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    session_age = datetime.now() - start_time
                    if session_age.total_seconds() > 86400:  # 24 hours
                        # Auto-end stale session
                        session.metadata["ended"] = True
                        session.metadata["end_reason"] = "session_timeout"
                        save_session(session)
                        return {
                            "success": False,
                            "response": "This conversation has expired. Please start a new survey.",
                            "error": "session_expired"
                        }
                except ValueError:
                    pass  # Continue if timestamp parsing fails
            
            # Check if form is still active
            form_doc = firestore_db.collection("forms").document(session.form_id).get()
            if not form_doc.exists:
                return {
                    "success": False,
                    "response": "Sorry, this survey is no longer available.",
                    "error": "form_not_found"
                }
            
            form_data = form_doc.to_dict()
            if not form_data.get("active", False):
                return {
                    "success": False,
                    "response": "Sorry, this survey is currently unavailable.",
                    "error": "form_inactive"
                }

            # Check for conversation break (more than 2 minutes since last message)
            now = datetime.now()
            recap_needed = False
            if session.chat_history:
                try:
                    timestamp = session.chat_history[-1]["timestamp"]
                    if isinstance(timestamp, str):
                        last_msg_time = datetime.fromisoformat(timestamp)
                        time_gap = now - last_msg_time
                        if time_gap.total_seconds() > 120:  # 2 minutes
                            recap_needed = True
                except (ValueError, KeyError):
                    # Skip recap if timestamp parsing fails
                    pass

            # Add user message to history
            session.chat_history.append(
                {
                    "role": "user",
                    "content": user_message,
                    "timestamp": now.isoformat(),
                }
            )

            # Agent will use tools to understand current state - no hints needed
            
            # Generate recap if needed
            recap_context = ""
            if recap_needed:
                answered_count = len([r for r in session.responses.values() if r.get("value") != "[SKIP]"])
                total_questions = len([q for q in session.form_data.get("questions", []) if q.get("enabled", True)])
                recap_context = f"\n[NOTE: Session resumed - {answered_count}/{total_questions} questions completed so far. Respond to their message naturally.]\n"
            
            # Get recent conversation history for context
            recent_history = session.chat_history[-6:] if len(session.chat_history) > 6 else session.chat_history
            history_context = ""
            if recent_history:
                history_context = "\nRecent conversation:\n"
                for msg in recent_history:
                    role_label = "User" if msg["role"] == "user" else "You"
                    history_context += f"{role_label}: {msg['content']}\n"
            
            # Prepare input for the agent with minimal context (NO RAW QUESTION TEXT)
            bot_context = session.form_data.get('bot_context', '').strip()
            context_section = f"\nBot Context: {bot_context}\n" if bot_context else ""
            
            agent_input = f"""
Current session: {session_id}
Form: {session.form_data.get('title', 'Survey')}{context_section}
Progress: Question {session.current_question_index + 1} of {len(session.form_data.get('questions', []))}
{recap_context}
{history_context}
User just said: "{user_message}"

Use your tools to understand the situation and respond naturally."""

            # Run the agent
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            print(f"DEBUG: Running agent with input: {agent_input}")
            # Increase max_turns from default 10 to 100 for surveys with many questions
            result = Runner.run_sync(self.agent, agent_input, max_turns=100)
            print(f"DEBUG: Agent result: {result}")

            # Extract response
            agent_response = (
                result.final_output if hasattr(result, "final_output") else str(result)
            )
            print(f"DEBUG: Agent response: {agent_response}")

            # Add agent response to history
            session.chat_history.append(
                {
                    "role": "assistant",
                    "content": agent_response,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Reload session to get any updates from tool calls
            updated_session = load_session(session_id)

            # Extract chip options by calling get_natural_question for current state
            chip_options = None
            try:
                current_q_idx = updated_session.current_question_index
                questions = updated_session.form_data.get("questions", [])
                ended = updated_session.metadata.get("ended", False)
                
                print(f"DEBUG: current_q_idx={current_q_idx}, questions_count={len(questions)}, ended={ended}")
                
                # If we're asking a question (not ended), get chip options
                if current_q_idx < len(questions) and not ended:
                    current_q = questions[current_q_idx]
                    q_type = current_q.get("type", "text")
                    q_text = current_q.get("text", "")
                    
                    print(f"DEBUG: current question - type={q_type}, text={q_text}")
                    
                    natural_q_result = _get_natural_question_data(
                        session_id, 
                        q_text, 
                        q_type, 
                        current_q_idx
                    )
                    print(f"DEBUG: get_natural_question result: {natural_q_result}")
                    
                    if natural_q_result.get("show_chips"):
                        chip_options = {
                            "show_chips": True,
                            "chip_type": natural_q_result.get("chip_type"),
                            "options": natural_q_result.get("chip_options", [])
                        }
                        print(f"DEBUG: Setting chip_options: {chip_options}")
                    else:
                        print(f"DEBUG: No chips to show for type {q_type}")
                else:
                    print(f"DEBUG: Not showing chips - ended or no more questions")
            except Exception as e:
                print(f"DEBUG: Error extracting chip options: {e}")
                import traceback
                print(f"DEBUG: Traceback: {traceback.format_exc()}")

            return {
                "success": True,
                "response": agent_response,
                "session_updated": True,
                "metadata": updated_session.metadata,
                "chip_options": chip_options,  # Add chip support
                "debug_signature": "NEW_OPENAI_AGENTS_v2.0",  # Version signature
            }

        except Exception as e:
            # Log the actual error for debugging
            import traceback

            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"CHAT AGENT ERROR: {error_details}")

            return {
                "success": False,
                "error": f"Message processing failed: {str(e)}",
                "response": "I'm having trouble right now. Could you try again? 😅",
            }


# Global agent instance
chat_agent = None


def get_chat_agent():
    """Get or create the global chat agent instance"""
    global chat_agent
    if chat_agent is None:
        import sys
        import datetime
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        print(f"=== CHAT ENGINE VERSION CHECK ===", file=sys.stderr)
        print(f"TIMESTAMP: {datetime.datetime.now().isoformat()}", file=sys.stderr)
        print(f"CHAT ENGINE: Using NEW system with industry safety rules (v2.0)", file=sys.stderr)
        print(f"DEBUG: API key available: {bool(openai_api_key)}", file=sys.stderr)
        print(f"DEBUG: API key length: {len(openai_api_key) if openai_api_key else 0}", file=sys.stderr)
        print(f"DEBUG: Python version: {sys.version}", file=sys.stderr)
        
        # Check if agents module is available
        try:
            import agents
            print(f"DEBUG: agents module available: {agents.__version__ if hasattr(agents, '__version__') else 'unknown version'}", file=sys.stderr)
        except ImportError as e:
            print(f"CRITICAL: agents module not available: {e}", file=sys.stderr)
            raise ImportError(f"OpenAI Agents SDK not installed: {e}")
        
        if openai_api_key:
            print(f"DEBUG: API key prefix: {openai_api_key[:10]}...", file=sys.stderr)
            print(f"DEBUG: API key ends with newline: {repr(openai_api_key[-2:])}", file=sys.stderr)

        if not openai_api_key:
            print("ERROR: OPENAI_API_KEY environment variable not set", file=sys.stderr)
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        try:
            chat_agent = FormChatAgent(openai_api_key)
            print("DEBUG: Chat agent created successfully", file=sys.stderr)
        except Exception as e:
            print(f"CRITICAL: Failed to create FormChatAgent: {e}", file=sys.stderr)
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}", file=sys.stderr)
            raise
    return chat_agent