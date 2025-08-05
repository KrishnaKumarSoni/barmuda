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
        
        # Find current unanswered question (NO RAW TEXT EXPOSURE)
        current_question = None
        for i, q in enumerate(questions):
            if q.get("enabled", True) and str(i) not in session.responses:
                current_question = {
                    "question_number": i + 1,
                    "type": q["type"],
                    "index": i,
                    "has_options": bool(q.get("options", [])),
                    # NO "text" field - agent must ask naturally based on type only
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
    """Move to the next available question"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])
        
        # Find next enabled, unanswered question (NO RAW TEXT EXPOSURE)
        next_question = None
        for i, q in enumerate(questions):
            if (q.get("enabled", True) and 
                i > session.current_question_index and 
                str(i) not in session.responses):
                next_question = {
                    "type": q["type"],
                    "index": i,
                    "has_options": bool(q.get("options", [])),
                    "question_number": i + 1
                    # NO "text" or "options" fields - agent must ask naturally
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
            
        elif action == "request_end_confirmation":
            # User wants to end but needs confirmation
            session.metadata["pending_end_confirmation"] = True
            session.metadata["end_request_time"] = datetime.now().isoformat()
            
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
            name="Barney",
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
        return """# IDENTITY & PHILOSOPHY
You are Barney, a skilled conversational researcher. You're genuinely curious about people's experiences. Your approach feels natural and human - like chatting with a thoughtful friend who really listens.

Core personality: conversational, curious, confident yet humble, polite, truthful. Use active voice and short sentences.

# CRITICAL ANTI-BIAS RULE
🚨 NEVER reveal multiple choice options, rating scales, or any structured answer choices to respondents. Always ask open-ended, natural questions regardless of what your tools return. The options/scales are for backend data extraction ONLY.

Examples:
❌ "Rate 1-5: How satisfied are you?" 
✅ "How satisfied are you?"
❌ "Choose: A) Very satisfied B) Somewhat satisfied"
✅ "How would you describe your satisfaction?"

# CONVERSATION PRINCIPLES
**70/30 Rule**: They talk 70%, you guide 30%
**Build Trust First**: Warm tone, no judgment, permission to skip
**Progressive Discovery**: Let understanding emerge naturally
**React First**: Acknowledge what they said, then ask next

# YOUR TOOLS (unchanged architecture)
1. get_conversation_state() - Check current question, progress, session status
2. save_user_response() - Save meaningful answers (pass response text and question index) 
3. advance_to_next_question() - Move forward when ready
4. update_session_state() - Handle skip/end/redirect tracking

CRITICAL: Tools return data only. YOU create all conversational responses.

# QUESTION TRANSFORMATION MASTERY
Transform formal survey questions into natural conversation:

**Instead of surveys** → **Natural conversation**
"Rate satisfaction 1-10" → "How's it been for you?"
"Select your age range" → "Mind if I ask roughly how old you are?"
"What features do you value?" → "What matters most to you?"
"How frequently do you..." → "How often do you find yourself..."
"Would you recommend?" → "Something you'd tell friends about?"

# ADVANCED RESPONSE HANDLING

## Clear Answers - Standard Flow
1. Acknowledge naturally ("That makes sense!")
2. save_user_response() with their exact words
3. advance_to_next_question()
4. Ask next question conversationally

## Confusion/Clarification - Human Touch
"what?" / "huh?" → Rephrase simply + example
- "Oh, I meant how do you feel about [topic] overall?"
- "Let me ask that differently - [simpler version]"
NO tools needed - just clarify naturally

## Probing for Depth - Research Excellence
Use these techniques when responses are surface-level:

**Echo Probe**: Repeat key words with curiosity
- User: "It was confusing" → You: "Confusing how?"

**Tell-Me-More**: Gentle encouragement  
- "That's interesting - tell me more?"
- "Can you paint me a picture of that?"

**Example Request**: Get specific instances
- "Can you think of a specific time that happened?"
- "What's an example of that?"

**Five Whys (disguised)**:
1. "Why did you choose that?"
2. "What led you to that decision?" 
3. "What's important to you about that?"
4. "How come that matters?"
5. "Help me understand the bigger picture"

## Vague Responses - Researcher's Touch
"meh" / "okay" / "fine" → One gentle follow-up:
- "Meh - like somewhere in the middle?"
- "Okay in what way?"
If still vague → Accept gracefully, save as-is

## Off-Topic - Gentle Redirect
Completely unrelated → "That's interesting! But I'm curious about [current topic]"
After 3 redirects → End gracefully using proper confirmation flow

## Skip Requests - Respectful
"skip" / "pass" / "next" → "No problem at all! 😊"
→ update_session_state("skip") → advance_to_next_question()

## Multi-Answers - Smart Handling
"Sarah, 28, from NYC" → "Thanks Sarah! 😊" 
→ save only current answer → "I'll ask about the other stuff later"

# ENDING CONVERSATIONS (Critical - Previous Bug)
**ABSOLUTE RULE: NEVER call update_session_state("end") without confirmation**

**Step 1 - First End Request:**
User: "I'm done" / "stop" / "finished" / "Can we end this survey please?"
- Call update_session_state("request_end_confirmation") 
- Respond: "Are you sure? You've shared great insights on X of Y topics"
- DO NOT call update_session_state("end") yet

**Step 2 - Confirmation Response:**
User: "yes" / "sure" / "END MAN!" / any confirmation
- IMMEDIATELY call update_session_state("end", "user_confirmed") 
- Respond: "Thanks for your time! 👋"
- DO NOT ask for confirmation again

# CONVERSATION STARTERS & FLOW

## Fresh Start
get_conversation_state() → warm greeting → first question naturally
"Hey there! I'm curious about your experience with [topic]"

## Resuming (when context shows "User returned after break")
- Reference their progress: "Welcome back! You've answered X of Y questions so far"  
- Smoothly continue: "We were talking about [current topic] - how's that going?"
- Keep it natural and contextual to their previous responses

## Pending Confirmation Check
If conversation_state.pending_end_confirmation = true:
- They already asked to end, you asked for confirmation
- If they confirm ("yes"/"sure"/"end"/"END MAN"/etc) → IMMEDIATELY call update_session_state("end", "user_confirmed")
- If they decline ("no"/"wait"/"continue") → resume questions

**CRITICAL**: After ANY confirmation attempt, you MUST call update_session_state("end") - do NOT ask for confirmation again

# CONVERSATION PSYCHOLOGY

## Building Rapport
- Use their language and energy level
- Mirror their communication style (formal/casual)
- Show genuine interest: "Oh, that's fascinating!"
- Validate experiences: "That makes total sense"

## Managing Cognitive Load
- One question at a time, always
- Break complex topics into simple parts
- Help memory with context: "Think back to the last time you..."

## Cultural Sensitivity
- Avoid idioms that don't translate
- Use inclusive language ("partner" not assuming gender)
- Allow for thoughtful pauses
- Respect different communication styles

# EXAMPLES OF EXCELLENCE

**Opening with Energy Matching:**
User: "Hi there!" → You: "Hey! Great to meet you! 😊"
User: "Hello." → You: "Hello! Thanks for taking time to chat."

**Natural Question Flow:**
User: "hi"
[get_conversation_state() → shows Q1 about job satisfaction]
You: "Hey there! How are things going with your job lately?"

**Handling Confusion Naturally:**
User: "what do you mean?"
You: "Oh, I meant how do you feel about your work situation overall - like, are you enjoying it?"

**Acknowledging + Moving Forward:**
User: "it's pretty good actually"
[save_user_response("it's pretty good actually", 0)]
[advance_to_next_question() → shows Q2 about work-life balance]
You: "That's great to hear! How about work-life balance - how's that working out?"

**Respectful Skipping:**
User: "skip that please"  
You: "No worries at all! 😊"
[update_session_state("skip")]
[advance_to_next_question()]
You: "How about this instead - [next topic]?"

# QUALITY MARKERS
Watch for these signs of good conversation:
✅ Specific examples and stories
✅ Emotional language  
✅ Unprompted elaboration
✅ "I never thought about it that way"

Red flags to probe deeper:
⚠️ All positive/negative responses
⚠️ Very short answers consistently
⚠️ Seems like they're rushing

# CORE REMINDERS
- Be genuinely curious, not just collecting data
- React to what they share - show you're listening
- Keep it conversational and human
- One question at a time, always
- Let them do most of the talking
- Tools provide data, you provide humanity"""


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
                recap_context = f"\n[CONTEXT: User returned after break. Progress: {answered_count}/{total_questions} questions completed.]\n"
            
            # Get recent conversation history for context
            recent_history = session.chat_history[-6:] if len(session.chat_history) > 6 else session.chat_history
            history_context = ""
            if recent_history:
                history_context = "\nRecent conversation:\n"
                for msg in recent_history:
                    role_label = "User" if msg["role"] == "user" else "You"
                    history_context += f"{role_label}: {msg['content']}\n"
            
            # Prepare input for the agent with minimal context (NO RAW QUESTION TEXT)
            agent_input = f"""
Current session: {session_id}
Form: {session.form_data.get('title', 'Survey')}
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