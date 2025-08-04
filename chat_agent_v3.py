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
from agents import Agent, Runner, function_tool
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

# Initialize Firebase if not already done
if not firebase_admin._apps:
    cred = firebase_admin.credentials.Certificate(
        "barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json"
    )
    firebase_admin.initialize_app(
        cred, {"databaseURL": "https://barmuda-in-default-rtdb.firebaseio.com/"}
    )

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
    """Load session from Firebase or memory"""
    if session_id in active_sessions:
        return active_sessions[session_id]

    # Load from Firestore
    session_doc = firestore_db.collection("chat_sessions").document(session_id).get()

    if session_doc.exists:
        session_data = session_doc.to_dict()
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
        
        # Find current unanswered question
        current_question = None
        for i, q in enumerate(questions):
            if q.get("enabled", True) and str(i) not in session.responses:
                current_question = {
                    "text": q["text"],
                    "type": q["type"],
                    "index": i,
                    "options": q.get("options", [])
                }
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
                "time_elapsed": _calculate_time_elapsed(session.metadata.get("start_time"))
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
        
        # Save response
        session.responses[str(question_index)] = {
            "value": response_text,
            "timestamp": datetime.now().isoformat(),
            "question_text": session.form_data["questions"][question_index]["text"]
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
    """Move to the next available question"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])
        
        # Find next enabled, unanswered question
        next_question = None
        for i, q in enumerate(questions):
            if (q.get("enabled", True) and 
                i > session.current_question_index and 
                str(i) not in session.responses):
                next_question = {
                    "text": q["text"],
                    "type": q["type"],
                    "index": i,
                    "options": q.get("options", [])
                }
                session.current_question_index = i
                break
        
        save_session(session)
        
        # Check if all questions completed
        enabled_questions = [q for q in questions if q.get("enabled", True)]
        answered_count = len([r for r in session.responses.values() if r.get("value") != "[SKIP]"])
        all_completed = answered_count >= len(enabled_questions)
        
        return {
            "advanced": True,
            "next_question": next_question,
            "all_questions_completed": all_completed,
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
            session.metadata["ended"] = True
            session.metadata["end_time"] = datetime.now().isoformat()
            session.metadata["end_reason"] = reason
            # Calculate if partial
            enabled_count = len([q for q in session.form_data.get("questions", []) if q.get("enabled", True)])
            answered_count = len([r for r in session.responses.values() if r.get("value") != "[SKIP]"])
            session.metadata["partial"] = answered_count < enabled_count * 0.8
            
        elif action == "redirect":
            session.metadata["redirect_count"] += 1
            
        elif action == "timeout":
            session.metadata["partial"] = True
            session.metadata["timeout"] = True
            
        save_session(session)
        
        return {
            "action_completed": True,
            "action": action,
            "session_ended": session.metadata.get("ended", False),
            "redirect_count": session.metadata.get("redirect_count", 0)
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

        # Ensure event loop exists for async operations
        import asyncio

        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Create agent with simplified tools
        self.agent = Agent(
            name="Alex",
            model="gpt-4o-mini",
            instructions=self._get_system_instructions(),
            tools=[
                get_conversation_state,
                save_user_response,
                advance_to_next_question,
                update_session_state
            ],
        )

    def _get_system_instructions(self) -> str:
        """Get system instructions for the agent"""
        return """# IDENTITY
You are Alex, a warm and friendly person having a natural conversation to learn about someone's experience. You're genuinely curious and empathetic.

# CONVERSATION STYLE
- Keep responses 1-2 sentences maximum
- Sound natural, like texting a friend
- React to what they say first, then guide conversation
- Never sound robotic or corporate

# TOOL USAGE
You have 4 tools that provide data. Use them to understand context and manage conversation:

1. get_conversation_state() - Check current question, progress, session status
2. save_user_response() - Save meaningful answers (pass response text and question index)
3. advance_to_next_question() - Move forward when ready
4. update_session_state() - Handle skip/end/redirect tracking

IMPORTANT: Tools return data only. YOU create all conversational responses.

# CONVERSATION FLOW

## Starting/Resuming Conversations
- Fresh start: Use get_conversation_state(), greet warmly, ask first question naturally
- Resuming (context shows elapsed time > 120s): "Welcome back! We were talking about [topic]..."
- Completed survey: "Thanks for completing the survey! Your responses have been saved."

## Asking Questions
Transform formal questions naturally:
- "How satisfied are you with your current role?" → "How do you feel about your job?"
- "Rate your work-life balance" → "How's your work-life balance?"
- "How would you rate the organization?" → "How was it organized?"

## Handling User Responses

### Clear Answers
User gives meaningful response → save_user_response() → acknowledge naturally → advance_to_next_question() → ask next naturally

### Confusion/Clarification
"what?" / "what do you mean?" / "huh?" → Rephrase more simply without tools
Example: "Sorry! I meant how do you feel about your job overall?"

### Off-Topic
Completely unrelated → "That's a bit bananas! 😄 But I'm curious about [current topic]"
After 3 redirects (check redirect_count) → End conversation gracefully

### Skip Requests
"skip" / "pass" / "next" → "No problem! 😊" → update_session_state("skip") → advance_to_next_question()

### End Requests
"I'm done" / "stop" → "Are you sure you want to stop? You've answered X of Y questions."
If confirmed → update_session_state("end") → "Thanks for your time! 👋"

### Vague Responses
"meh" / "okay" / "fine" → "Meh—like a 2 or 3?" (one follow-up only)
Still vague → Accept and save as-is (extraction handles mapping)

### Multi-Answers
"Alex, 25, from LA" → "Great, thanks Alex! 😎" → save only current answer → mention you'll ask about rest later

### Wrong Type
"How many?" "Several" → "Several—like 2 or 3? 😺"

# EXAMPLES

User: "hi"
[get_conversation_state() → shows question 1]
You: "Hey there! How do you feel about your job?"

User: "what?"
You: "Sorry! I meant how satisfied are you with your work overall?"

User: "it's pretty good actually"
[save_user_response("it's pretty good actually", 0)]
[advance_to_next_question() → shows question 2]
You: "That's great! And how's your work-life balance?"

User: "skip that"
You: "No worries! 😊"
[update_session_state("skip")]
[advance_to_next_question() → shows question 3]
You: "How about the management—how's that going?"

# REMEMBER
- React naturally to what they say
- Use tools for data, create your own responses
- Keep it conversational and brief
- Handle confusion with clarification, not tools
- Let extraction pipeline handle complex data processing"""

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

            # Check for conversation break (more than 2 minutes since last message)
            now = datetime.now()
            recap_needed = False
            if session.chat_history:
                last_msg_time = datetime.fromisoformat(session.chat_history[-1]["timestamp"])
                time_gap = now - last_msg_time
                if time_gap.total_seconds() > 120:  # 2 minutes
                    recap_needed = True

            # Add user message to history
            session.chat_history.append(
                {
                    "role": "user",
                    "content": user_message,
                    "timestamp": now.isoformat(),
                }
            )

            # Get current question context
            current_q_idx = session.current_question_index
            current_question = ""
            if current_q_idx < len(session.form_data.get("questions", [])):
                current_question = session.form_data["questions"][current_q_idx]["text"]
            
            # Generate recap if needed
            recap_context = ""
            if recap_needed:
                answered_count = len([r for r in session.responses.values() if r.get("value") != "[SKIP]"])
                total_questions = len([q for q in session.form_data.get("questions", []) if q.get("enabled", True)])
                recap_context = f"\n[CONTEXT: User returned after break. Progress: {answered_count}/{total_questions} questions completed. Current topic: {current_question}]\n"
            
            # Get recent conversation history for context
            recent_history = session.chat_history[-6:] if len(session.chat_history) > 6 else session.chat_history
            history_context = ""
            if recent_history:
                history_context = "\nRecent conversation:\n"
                for msg in recent_history:
                    role_label = "User" if msg["role"] == "user" else "You"
                    history_context += f"{role_label}: {msg['content']}\n"
            
            # Prepare input for the agent with full context
            agent_input = f"""
Current session: {session_id}
Form: {session.form_data.get('title', 'Survey')}
Progress: Question {session.current_question_index + 1} of {len(session.form_data.get('questions', []))}
Current Question: "{current_question}"
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
            result = Runner.run_sync(self.agent, agent_input)
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

            return {
                "success": True,
                "response": agent_response,
                "session_updated": True,
                "metadata": updated_session.metadata,
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
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        print(f"DEBUG: API key available: {bool(openai_api_key)}")
        print(f"DEBUG: API key length: {len(openai_api_key) if openai_api_key else 0}")
        if openai_api_key:
            print(f"DEBUG: API key prefix: {openai_api_key[:10]}...")
            print(f"DEBUG: API key ends with newline: {repr(openai_api_key[-2:])}")

        if not openai_api_key:
            print("ERROR: OPENAI_API_KEY environment variable not set")
            raise ValueError("OPENAI_API_KEY environment variable not set")
        chat_agent = FormChatAgent(openai_api_key)
        print("DEBUG: Chat agent created successfully")
    return chat_agent