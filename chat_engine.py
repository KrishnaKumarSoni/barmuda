
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import firebase_admin
import google.generativeai as genai
from dotenv import load_dotenv
from firebase_admin import firestore

# Load environment variables
load_dotenv()

# --- Firebase and Gemini Initialization ---

# This assumes Firebase is initialized in app.py.
# For standalone testing, the original fallback logic is kept.
if not firebase_admin._apps:
    cred_path = "barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json"
    if os.path.exists(cred_path):
        cred = firebase_admin.credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        print("WARNING: Firebase credentials not found for standalone mode.")

firestore_db = firestore.client()

# Configure Gemini
try:
    google_api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if google_api_key:
        genai.configure(api_key=google_api_key)
    else:
        print("CRITICAL: GOOGLE_API_KEY not found.")
except AttributeError:
    print("CRITICAL: The installed 'google.generativeai' library is too old or incorrect. `genai.configure` not found.")
except Exception as e:
    print(f"CRITICAL: Failed to configure Gemini: {e}")


# --- Data Structures and Session Management ---

@dataclass
class ChatSession:
    """
    Manages the state of a chat session. The schema is kept identical to the
    previous version for seamless compatibility with the rest of the codebase.
    """
    session_id: str
    form_id: str
    form_data: Dict
    responses: Dict[str, Any] = field(default_factory=dict)
    current_question_index: int = 0
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {
                "start_time": datetime.now().isoformat(),
                "skip_count": 0,
                "ended": False,
            }

# In-memory cache to reduce Firestore reads for active sessions.
# A proper solution would use Redis with a TTL.
active_sessions: Dict[str, ChatSession] = {}

def load_session(session_id: str) -> Optional[ChatSession]:
    """
    Loads a session from the in-memory cache or Firestore.
    Maintains compatibility with the previous implementation.
    """
    if session_id in active_sessions:
        return active_sessions[session_id]

    try:
        session_doc = firestore_db.collection("chat_sessions").document(session_id).get()
        if session_doc.exists:
            session_data = session_doc.to_dict()
            # Ensure responses has string keys, a common Firestore-related issue
            if 'responses' in session_data:
                session_data['responses'] = {str(k): v for k, v in session_data['responses'].items()}
            session = ChatSession(**session_data)
            active_sessions[session_id] = session
            return session
    except Exception as e:
        print(f"ERROR: Failed to load session {session_id}: {e}")
    return None

def save_session(session: ChatSession):
    """
    Saves a session to both the in-memory cache and Firestore.
    If the session has ended, it also writes to the 'chat_responses' collection
    for the dashboard, maintaining a critical gotcha from the old system.
    """
    active_sessions[session.session_id] = session
    session_data = {
        "session_id": session.session_id,
        "form_id": session.form_id,
        "form_data": session.form_data,
        "responses": session.responses,
        "current_question_index": session.current_question_index,
        "chat_history": session.chat_history,
        "metadata": session.metadata,
        "last_updated": datetime.now().isoformat(),
    }
    
    doc_ref = firestore_db.collection("chat_sessions").document(session.session_id)
    doc_ref.set(session_data, merge=True)

    if session.metadata.get("ended", False):
        firestore_db.collection("chat_responses").document(session.session_id).set(session_data)
        # Clean up from active cache once ended
        if session.session_id in active_sessions:
            del active_sessions[session.session_id]

def _get_natural_question_data(
    session_id: str, question_text: str, question_type: str, question_index: int
) -> dict:
    """Helper function to get natural question data (used both by tool and chip extraction)"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])
        current_q = questions[question_index] if question_index < len(questions) else {}

        # Common conversational starters
        starters = ["Hey!", "So,", "Alright,", "Cool,", "Nice,", "Great,"]
        starter = (
            starters[question_index % len(starters)] if question_index > 0 else "Hey!"
        )

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
                natural_question = (
                    f"{starter} {question_text}"
                    if not question_text.startswith(("Do", "Are", "Is", "Can", "Would"))
                    else question_text
                )
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

        return {
            "natural_question": natural_question.capitalize(),
            "show_chips": show_chips,
            "chip_options": ui_options,
            "chip_type": question_type if show_chips else None,
        }

    except Exception as e:
        # Fallback to original question
        return {
            "natural_question": question_text,
            "show_chips": False,
            "chip_options": [],
            "error": str(e),
        }
# --- Deterministic Engine Core ---

class DeterministicChatAgent:
    """
    A deterministic chat engine that follows a reliable, state-machine-like
    process. It uses Gemini only for natural language generation, not for logic.
    """
    def __init__(self):
        try:
            self.model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception as e:
            print(f"CRITICAL: Failed to initialize Gemini Model: {e}")
            self.model = None

    def create_session(self, form_id: str, device_id: str = None, location: Dict = None) -> str:
        """
        Creates a new chat session. Logic is identical to the previous version
        to ensure compatibility.
        """
        form_doc = firestore_db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            raise ValueError(f"Form {form_id} not found")

        form_data = form_doc.to_dict()
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        session = ChatSession(
            session_id=session_id,
            form_id=form_id,
            form_data=form_data,
            metadata={
                "start_time": datetime.now().isoformat(),
                "device_id": device_id,
                "location": location,
                "skip_count": 0,
                "ended": False,
            }
        )
        save_session(session)
        return session_id

    def _get_next_question(self, session: ChatSession) -> Optional[Dict]:
        """Deterministically finds the next unanswered question."""
        questions = session.form_data.get("questions", [])
        start_index = session.current_question_index
        
        for i in range(start_index, len(questions)):
            question = questions[i]
            if question.get("enabled", True) and str(i) not in session.responses:
                session.current_question_index = i
                return {**question, "index": i}
        
        session.current_question_index = len(questions)
        return None

    def _validate_and_save_response(self, session: ChatSession, question_index: int, user_message: str):
        """Saves the user's message as the response to the specified question."""
        questions = session.form_data.get("questions", [])
        if question_index < len(questions):
            session.responses[str(question_index)] = {
                "value": user_message,
                "timestamp": datetime.now().isoformat(),
                "question_text": questions[question_index].get("text", "")
            }

    def _get_chips_for_question(self, question: Optional[Dict]) -> Optional[Dict]:
        """Deterministically generates UI chips for a given question."""
        if not question:
            return None
        
        q_type = question.get("type")
        if q_type == "yes_no":
            return {"show_chips": True, "options": ["Yes", "No"]}
        if q_type == "rating":
            return {"show_chips": True, "options": [str(i) for i in range(1, 6)]}
        if q_type == "multiple_choice" and question.get("options"):
            return {"show_chips": True, "options": question["options"][:5]}
        
        return None
        
    def _get_conversational_prompt(self, session: ChatSession, last_answer: str, next_question_text: str, is_first_message: bool) -> str:
        """Generates a high-quality prompt for Gemini to give the agent a dynamic, human-like persona."""
        
        default_persona = "You are Alex, a curious and empathetic researcher. Your goal is to make this feel like a natural chat."
        
        # Dynamically get persona from form_data, with a fallback.
        persona = session.form_data.get("persona", default_persona).strip()
        if not persona or not persona.startswith("You are"):
            persona = default_persona

        if is_first_message:
            return f"""{persona}

Your Task: Kick off the conversation by asking the first question in a friendly, welcoming way.

First Question: \"{next_question_text}\"\n"""

        if not next_question_text:
             return f"""{persona}

User's final answer was: \"{last_answer}\"\n
Your Task: That was the last question! Thank them warmly for their time and insights. End the conversation on a positive note."""

        return f"""{persona}
        
Your Task: Make this feel like a natural conversation, not an interrogation.
1. Acknowledge the user's last answer (\"{last_answer}\") in a thoughtful, human way.
2. Smoothly transition and ask the next question: \"{next_question_text}\"\nKeep your entire response to 1-2 friendly sentences.

Example: If the last answer was \"The UI was clunky\" and the next question is \"How often do you use it?\", a great response is:
\"I hear you on the clunky UI, that's really helpful feedback. Speaking of which, how often do you find yourself using it?\""""

    def _get_templated_response(self, last_answer: str, next_question_text: str) -> str:
        """Generates a fast, non-LLM, templated response."""
        acknowledgements = ["Got it.", "Thanks.", "Okay.", "Perfect."]
        # Simple rotation of acknowledgements
        ack = acknowledgements[len(last_answer) % len(acknowledgements)]
        return f"{ack} {next_question_text}"

    def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        session = load_session(session_id)
        if not session:
            return {"success": False, "response": "Session not found.", "error": "session_not_found"}

        if session.metadata.get("ended"):
            return {"success": True, "response": "This conversation has already ended. Thank you!", "ended": True, "chip_options": None}

        is_first_interaction = not session.chat_history or len(session.chat_history) <= 1

        if not is_first_interaction:
            self._validate_and_save_response(session, session.current_question_index, user_message)

        session.chat_history.append({'role': 'user', 'parts': [user_message]})
        
        next_question = self._get_next_question(session)

        agent_response = ""
        
        # --- Hybrid Engine Logic ---
        # Decide whether to use the fast path or the conversational LLM path.
        # Heuristic: Use LLM for long answers or the very first question.
        use_llm = is_first_interaction or len(user_message.split()) > 15

        if use_llm:
            try:
                if not self.model:
                    raise ConnectionError("Gemini model not initialized.")
                
                prompt = self._get_conversational_prompt(
                    session,
                    user_message, 
                    next_question.get("text", "") if next_question else "",
                    is_first_interaction
                )
                response = self.model.generate_content(prompt)
                agent_response = response.text
            except Exception as e:
                print(f"ERROR: Gemini call failed: {e}. Falling back to deterministic response.")
                # Fallback to templated response on API error
                agent_response = self._get_templated_response(
                    user_message,
                    next_question.get("text", "") if next_question else "Thank you for your time!"
                )
        else:
            # Fast Path: Use a template for simple acknowledgements
            agent_response = self._get_templated_response(
                user_message,
                next_question.get("text", "") if next_question else "Thank you for completing the survey!"
            )

        if not next_question:
            session.metadata["ended"] = True

        session.chat_history.append({'role': 'model', 'parts': [agent_response]})
        
        save_session(session)

        return {
            "success": True,
            "response": agent_response,
            "session_updated": True,
            "metadata": session.metadata,
            "chip_options": self._get_chips_for_question(next_question),
            "debug_signature": "DETERMINISTIC_HYBRID_GEMINI_v4.5",
        }

# --- Singleton Pattern for Agent ---
_chat_agent_instance = None

def get_chat_agent() -> DeterministicChatAgent:
    """Returns the singleton instance of the chat agent."""
    global _chat_agent_instance
    if _chat_agent_instance is None:
        _chat_agent_instance = DeterministicChatAgent()
    return _chat_agent_instance
