"""
Barmuda Groq Chat Agent - High-Speed Alternative to OpenAI Agents SDK
Implements same interface as chat_engine.py but uses Groq for 10x faster inference
"""

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import firebase_admin
from groq import Groq
from dotenv import load_dotenv
from firebase_admin import db, firestore

# Load environment variables
load_dotenv()

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

# Initialize Groq client
groq_client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

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
                "current_question_index": 0,
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
# TOOL FUNCTIONS - Same interface as OpenAI Agents SDK version
# ============================================================

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

def update_session_state(session_id: str, action: str, reason: str = "user_request") -> dict:
    """Update session state for skip, end, redirect tracking, etc."""
    try:
        session = load_session(session_id)
        
        if action == "skip":
            session.metadata["skip_count"] += 1
            current_idx = session.metadata.get("current_question_index", 0)
            session.responses[str(current_idx)] = {
                "value": "[SKIP]",
                "timestamp": datetime.now().isoformat(),
                "reason": reason
            }
            
        elif action == "redirect":
            session.metadata["redirect_count"] += 1
            
        elif action == "end":
            session.metadata["ended"] = True
            session.metadata["end_time"] = datetime.now().isoformat()
            
        elif action == "set_pending_end":
            session.metadata["pending_end_confirmation"] = True
            
        elif action == "clear_pending_end":
            session.metadata["pending_end_confirmation"] = False
        
        save_session(session)
        return {"updated": True, "action": action}
    except Exception as e:
        return {"updated": False, "error": str(e)}

def get_natural_question(session_id: str, question_index: int) -> dict:
    """Get natural question text for conversational flow"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])
        
        if question_index >= len(questions):
            return {"error": "Question index out of range"}
        
        question = questions[question_index]
        
        return {
            "text": question["text"],
            "type": question["type"],
            "options": question.get("options", []),
            "enabled": question.get("enabled", True),
            "index": question_index
        }
    except Exception as e:
        return {"error": str(e)}

def collect_demographic_data(session_id: str, demographic_type: str, value: str) -> dict:
    """Collect demographic data during conversation"""
    try:
        session = load_session(session_id)
        
        if "demographics_responses" not in session.metadata:
            session.metadata["demographics_responses"] = {}
        
        session.metadata["demographics_responses"][demographic_type] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        
        save_session(session)
        
        return {
            "collected": True,
            "demographic_type": demographic_type,
            "value": value
        }
    except Exception as e:
        return {"collected": False, "error": str(e)}

def collect_profile_data(session_id: str, profile_field: str, value: str) -> dict:
    """Collect profile data during conversation"""
    try:
        session = load_session(session_id)
        
        if "profile_responses" not in session.metadata:
            session.metadata["profile_responses"] = {}
        
        session.metadata["profile_responses"][profile_field] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        
        save_session(session)
        
        return {
            "collected": True,
            "profile_field": profile_field,
            "value": value
        }
    except Exception as e:
        return {"collected": False, "error": str(e)}

# Helper functions
def _calculate_time_elapsed(start_time_str: str) -> str:
    """Calculate time elapsed since session start"""
    try:
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        elapsed = datetime.now() - start_time.replace(tzinfo=None)
        minutes = int(elapsed.total_seconds() / 60)
        return f"{minutes} minutes"
    except:
        return "Unknown"

def _get_recent_responses(session: ChatSession, limit: int = 3) -> List[Dict]:
    """Get recent responses for context"""
    responses = list(session.responses.values())
    responses.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return responses[:limit]

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

# ============================================================
# GROQ CHAT AGENT IMPLEMENTATION
# ============================================================

class GroqChatAgent:
    """Groq-powered chat agent compatible with OpenAI Agents SDK interface"""
    
    def __init__(self, model="llama-3.3-70b-versatile"):
        self.model = model
        self.tools = self._define_tools()
        self.system_prompt = self._get_system_prompt()
    
    def _define_tools(self) -> List[Dict]:
        """Define tools for Groq function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_conversation_state",
                    "description": "Get current conversation state, progress, and context",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID to get state for"
                            }
                        },
                        "required": ["session_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_user_response",
                    "description": "Save user's response to a specific question",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID"
                            },
                            "response_text": {
                                "type": "string",
                                "description": "User's response text"
                            },
                            "question_index": {
                                "type": "integer",
                                "description": "Index of the question being answered"
                            }
                        },
                        "required": ["session_id", "response_text", "question_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "advance_to_next_question",
                    "description": "Move to the next available question after current is answered",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_session_state",
                    "description": "Update session state for skips, redirects, ending conversation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["skip", "redirect", "end", "set_pending_end", "clear_pending_end"],
                                "description": "Action to perform"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for the action",
                                "default": "user_request"
                            }
                        },
                        "required": ["session_id", "action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_natural_question",
                    "description": "Get the natural question text for conversational flow",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID"
                            },
                            "question_index": {
                                "type": "integer",
                                "description": "Index of the question to get"
                            }
                        },
                        "required": ["session_id", "question_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "collect_demographic_data",
                    "description": "Collect demographic information during conversation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID"
                            },
                            "demographic_type": {
                                "type": "string",
                                "description": "Type of demographic data (age, gender, etc.)"
                            },
                            "value": {
                                "type": "string",
                                "description": "The demographic value"
                            }
                        },
                        "required": ["session_id", "demographic_type", "value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "collect_profile_data",
                    "description": "Collect profile information during conversation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID"
                            },
                            "profile_field": {
                                "type": "string",
                                "description": "Type of profile data (name, email, etc.)"
                            },
                            "value": {
                                "type": "string",
                                "description": "The profile value"
                            }
                        },
                        "required": ["session_id", "profile_field", "value"]
                    }
                }
            }
        ]
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chat agent"""
        return """You are a friendly, empathetic conversational survey bot for Barmuda. Your job is to collect survey responses through natural conversation, making it feel like texting with a friend rather than filling out a boring form.

CRITICAL TOOL USAGE RULES:
- ALWAYS use the EXACT session_id provided in the conversation
- NEVER use "new_session" or make up session IDs
- For get_natural_question, use parameter name "question_index" NOT "question_id"
- Check get_conversation_state FIRST to understand what question you're on

CONVERSATION FLOW:
1. Start by calling get_conversation_state to understand current progress and get session context
2. If there's a current_question, get its details with get_natural_question using the question index
3. Ask the question naturally and conversationally
4. Process user's response:
   - Save valid responses using save_user_response with the correct question_index
   - Handle skips with update_session_state (action: "skip")
   - Handle off-topic with redirects (max 3 times, then skip)
   - Advance to next question when current is answered
5. Handle demographics and profile data collection when main questions complete
6. End with update_session_state (action: "end") when everything is done

CORE PRINCIPLES:
1. **Natural & Human-like**: Use emojis, casual language, slang. Be conversational, not robotic.
2. **One Question at a Time**: Ask ONE question, wait for response, then move on.
3. **Empathetic & Patient**: Handle skips, confusion, off-topic gracefully with understanding.
4. **Anti-Bias**: Ask questions openly without listing options (let users respond naturally).
5. **Chain of Thought**: Think through user responses to handle edge cases properly.

EDGE CASE HANDLING:
- **Off-topic ("bananas")**: Redirect gently 3x max, then move on
- **Skips**: Accept gracefully, mark as [SKIP], continue
- **Vague responses**: Ask for clarification once, then accept what you have
- **Conflicts**: Use latest response, clarify if needed
- **Multi-answers**: Parse and save relevant parts, note extras for later

RESPONSE STYLE:
- Use emojis appropriately 😊 ✨ 🎉
- Keep responses short and engaging
- Show progress occasionally ("Great! Just a few more...")
- Be encouraging and positive
- End with gratitude and celebration

Remember: You're making surveys feel human and enjoyable, not robotic or tedious!"""
    
    def _execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool function and return result"""
        tool_functions = {
            "get_conversation_state": get_conversation_state,
            "save_user_response": save_user_response,
            "advance_to_next_question": advance_to_next_question,
            "update_session_state": update_session_state,
            "get_natural_question": get_natural_question,
            "collect_demographic_data": collect_demographic_data,
            "collect_profile_data": collect_profile_data,
        }
        
        if tool_name in tool_functions:
            try:
                return tool_functions[tool_name](**arguments)
            except Exception as e:
                return {"error": f"Tool execution failed: {str(e)}"}
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def create_session(self, form_id: str, device_id: str = None, location: Dict = None) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        
        # Load form data from Firestore
        try:
            form_doc = firestore_db.collection("forms").document(form_id).get()
            if not form_doc.exists:
                raise ValueError(f"Form {form_id} not found")
            
            form_data = form_doc.to_dict()
            
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
                    "current_question_index": 0,
                }
            )
            
            save_session(session)
            return session_id
            
        except Exception as e:
            raise ValueError(f"Failed to create session: {str(e)}")
    
    def process_message(self, session_id: str, message: str) -> Dict:
        """Process a message and return response"""
        try:
            # Load session to get context
            session = load_session(session_id)
            
            # Add user message to history
            session.chat_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Build conversation context (last 10 messages)
            system_message_with_context = f"{self.system_prompt}\n\nCURRENT SESSION CONTEXT:\n- Session ID: {session_id}\n- Form: {session.form_data.get('title', 'Survey')}\n- IMPORTANT: Always use session_id '{session_id}' in ALL tool calls"
            messages = [{"role": "system", "content": system_message_with_context}]
            
            # Add recent chat history for context
            recent_history = session.chat_history[-10:]  # Last 10 messages
            for msg in recent_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Make Groq API call with tools
            response = groq_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )
            
            message = response.choices[0].message
            
            # Handle tool calls
            if message.tool_calls:
                # Execute each tool call
                tool_results = []
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    result = self._execute_tool(function_name, arguments)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "result": result
                    })
                
                # Add tool results to conversation and get final response
                messages.append(message)
                
                for tool_result in tool_results:
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(tool_result["result"]),
                        "tool_call_id": tool_result["tool_call_id"]
                    })
                
                # Get final response after tool execution
                final_response = groq_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                assistant_message = final_response.choices[0].message.content
            else:
                assistant_message = message.content
            
            # Add assistant response to history
            session.chat_history.append({
                "role": "assistant", 
                "content": assistant_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Save updated session
            save_session(session)
            
            return {
                "response": assistant_message,
                "session_id": session_id,
                "success": True
            }
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return {
                "response": "I'm having a moment - can you try that again? 😅",
                "error": str(e),
                "success": False
            }

# ============================================================
# COMPATIBILITY LAYER - Same interface as OpenAI Agents SDK
# ============================================================

def get_chat_agent():
    """Factory function to create chat agent - matches OpenAI Agents SDK interface"""
    return GroqChatAgent()

# For backwards compatibility
ChatAgent = GroqChatAgent