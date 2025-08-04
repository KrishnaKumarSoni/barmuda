"""
Barmuda Chat Agent - Agentic Chatbot for Form Collection (v2)
Uses OpenAI Agents SDK with standalone function tools
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


# Tool Functions (standalone functions with proper schemas)


@function_tool
def get_next_question(session_id: str) -> str:
    """Get the next question to ask in the form"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get("questions", [])

        # Find next enabled, unanswered question
        for i, question in enumerate(questions):
            if (
                question.get("enabled", True)
                and i >= session.current_question_index
                and str(i) not in session.responses
            ):

                # Update current question index
                session.current_question_index = i
                save_session(session)

                return f"Question {i+1}: {question['text']} (Type: {question['type']})"

        # No more questions
        return "All questions completed! Let me wrap this up for you. 🎉"

    except Exception as e:
        return f"Error getting next question: {str(e)}"


@function_tool
def skip_current_question(session_id: str, reason: str = "user_request") -> str:
    """Skip the current question and move to the next one"""
    try:
        session = load_session(session_id)
        current_idx = session.current_question_index

        # Mark as skipped
        session.responses[str(current_idx)] = {
            "value": "[SKIP]",
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
        }
        session.metadata["skip_count"] += 1

        # Move to next question
        session.current_question_index += 1
        save_session(session)

        return f"No worries! Question skipped. Let's move on to the next one. 😊"

    except Exception as e:
        return f"Error skipping question: {str(e)}"


@function_tool
def detect_skip_intent(session_id: str, user_message: str) -> str:
    """Detect if user wants to skip the current question using GPT"""
    try:
        # Use GPT to detect skip intent with fallback
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
            
            prompt = f"""Does this user message indicate they want to skip the current question?

User Message: "{user_message}"

Return JSON:
{{
    "wants_to_skip": true/false,
    "confidence": 0.0-1.0
}}

Examples:
"skip this" → {{"wants_to_skip": true, "confidence": 0.95}}
"I won't answer that, move on to the next" → {{"wants_to_skip": true, "confidence": 0.9}}
"pass" → {{"wants_to_skip": true, "confidence": 0.85}}
"I don't want to say" → {{"wants_to_skip": true, "confidence": 0.8}}
"next question please" → {{"wants_to_skip": true, "confidence": 0.9}}
"I love pizza" → {{"wants_to_skip": false, "confidence": 0.95}}
"maybe" → {{"wants_to_skip": false, "confidence": 0.7}}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )
            
            import json
            result = json.loads(response.choices[0].message.content.strip())
            
            if result.get("wants_to_skip", False) and result.get("confidence", 0) > 0.7:
                return skip_current_question(session_id, "gpt_detected_skip")
            else:
                return "not_skip_intent"
                
        except Exception as gpt_error:
            print(f"GPT skip detection failed: {str(gpt_error)}, using fallback")
            # Fallback to simple keyword detection
            skip_keywords = ["skip", "pass", "next", "move on", "don't want to answer", "won't answer"]
            if any(keyword in user_message.lower() for keyword in skip_keywords):
                return skip_current_question(session_id, "keyword_detected_skip")
            else:
                return "not_skip_intent"

    except Exception as e:
        print(f"Error in skip detection: {str(e)}")
        return "not_skip_intent"


@function_tool
def save_response(session_id: str, response_value: str) -> str:
    """Save a response to the current question WITHOUT advancing to next question"""
    try:
        session = load_session(session_id)
        current_idx = session.current_question_index

        if current_idx < len(session.form_data.get("questions", [])):
            session.responses[str(current_idx)] = {
                "value": response_value,
                "timestamp": datetime.now().isoformat(),
                "question_text": session.form_data["questions"][current_idx]["text"],
            }

            # DON'T auto-advance - let agent decide
            save_session(session)

            return f"Response saved. You can now ask follow-up or move to next question."
        else:
            return "All questions have been answered!"

    except Exception as e:
        return f"Error saving response: {str(e)}"


@function_tool
def move_to_next_question(session_id: str) -> str:
    """Move to the next question in the form"""
    try:
        session = load_session(session_id)
        session.current_question_index += 1
        save_session(session)
        
        # Get next question if available
        questions = session.form_data.get("questions", [])
        if session.current_question_index < len(questions):
            next_question = questions[session.current_question_index]["text"]
            return f"Moved to next question: {next_question}"
        else:
            session.metadata["completed"] = True
            save_session(session)
            return "All questions completed!"
            
    except Exception as e:
        return f"Error moving to next question: {str(e)}"


@function_tool
def redirect_conversation(session_id: str, user_message: str = "") -> str:
    """Handle off-topic responses by redirecting back to the form with GPT-generated bananas responses"""
    try:
        print(f"🎯 REDIRECT TOOL CALLED for session: {session_id}")
        session = load_session(session_id)
        session.metadata["redirect_count"] += 1

        if session.metadata["redirect_count"] >= 3:
            # Max redirects reached - end conversation
            session.metadata["ended"] = True
            session.metadata["end_reason"] = "max_redirects"
            save_session(session)
            return "I think we might be getting off track. Let's wrap up here. Thanks for your time! 👋"

        # Get current question for context
        current_q_idx = session.current_question_index
        current_question = ""
        if current_q_idx < len(session.form_data.get("questions", [])):
            current_question = session.form_data["questions"][current_q_idx]["text"]

        # Generate GPT bananas response with fallback
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
            
            prompt = f"""Generate a short, friendly redirect message with 'bananas' personality.
            
Current Question: "{current_question}"
Off-topic Message: "{user_message}"
Redirect Count: {session.metadata["redirect_count"]}/3

Requirements:
- Include the word "bananas" creatively
- Keep it short (1-2 sentences)
- Use 1-2 emojis
- Gently redirect back to the question
- Be conversational and fun

Examples:
"That's totally bananas! 😄 But let's focus on your hobby."
"Haha, bananas topic! 🍌 Back to the satisfaction rating though..."
"That's bananas! 😅 Let's get back to the question about your experience."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=60
            )
            
            gpt_response = response.choices[0].message.content.strip()
            print(f"🎯 GPT REDIRECT MESSAGE: {gpt_response}")
            save_session(session)
            return gpt_response
            
        except Exception as gpt_error:
            print(f"🎯 GPT REDIRECT FAILED: {str(gpt_error)}, using fallback")
            # Fallback to original hardcoded messages
            redirect_messages = [
                "That's a bit bananas! 😄 Let's focus on the form question.",
                "Interesting! But let's get back to the question at hand. 😊",
                "I'd love to chat about that later! Right now, let's focus on your response.",
            ]
            message_idx = min(
                session.metadata["redirect_count"] - 1, len(redirect_messages) - 1
            )
            save_session(session)
            return redirect_messages[message_idx]

    except Exception as e:
        print(f"🎯 REDIRECT ERROR: {str(e)}")
        return f"Error redirecting: {str(e)}"


@function_tool
def end_conversation(session_id: str, reason: str = "completion") -> str:
    """End the conversation and trigger data extraction"""
    try:
        session = load_session(session_id)
        session.metadata["ended"] = True
        session.metadata["end_time"] = datetime.now().isoformat()
        session.metadata["end_reason"] = reason

        # Determine if this is a partial completion
        total_questions = len(
            [
                q
                for q in session.form_data.get("questions", [])
                if q.get("enabled", True)
            ]
        )
        answered_questions = len(
            [r for r in session.responses.values() if r.get("value") != "[SKIP]"]
        )

        session.metadata["partial"] = (
            answered_questions < total_questions * 0.8
        )  # 80% threshold
        save_session(session)

        return f"Perfect! Thank you for completing the form. We received {answered_questions} responses. Have a great day! 🎉"

    except Exception as e:
        return f"Error ending conversation: {str(e)}"


@function_tool
def detect_end_intent(session_id: str, user_message: str) -> str:
    """Detect if user wants to end the survey using GPT"""
    try:
        # Use GPT to detect end intent with fallback
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
            
            prompt = f"""Does this user message indicate they want to end/quit/stop the survey?

User Message: "{user_message}"

Return JSON:
{{
    "wants_to_end": true/false,
    "confidence": 0.0-1.0
}}

Examples:
"I'm done" → {{"wants_to_end": true, "confidence": 0.9}}
"I want to no longer respond to this survey" → {{"wants_to_end": true, "confidence": 0.95}}
"stop this" → {{"wants_to_end": true, "confidence": 0.9}}
"I don't want to continue" → {{"wants_to_end": true, "confidence": 0.85}}
"enough questions" → {{"wants_to_end": true, "confidence": 0.8}}
"this is boring" → {{"wants_to_end": false, "confidence": 0.7}}
"I love pizza" → {{"wants_to_end": false, "confidence": 0.95}}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50
            )
            
            import json
            result = json.loads(response.choices[0].message.content.strip())
            
            if result.get("wants_to_end", False) and result.get("confidence", 0) > 0.8:
                return request_end_confirmation(session_id)
            else:
                return "not_end_intent"
                
        except Exception as gpt_error:
            print(f"GPT end detection failed: {str(gpt_error)}, using fallback")
            # Fallback to simple keyword detection
            end_keywords = ["done", "stop", "quit", "end", "finish", "enough", "no more"]
            if any(keyword in user_message.lower() for keyword in end_keywords):
                return request_end_confirmation(session_id)
            else:
                return "not_end_intent"

    except Exception as e:
        print(f"Error in end detection: {str(e)}")
        return "not_end_intent"


@function_tool
def request_end_confirmation(session_id: str) -> str:
    """Request confirmation before ending survey"""
    try:
        session = load_session(session_id)
        
        # Set confirmation state
        session.metadata.update({
            "state": "confirmation_pending",
            "confirmation_type": "end_survey"
        })
        
        # Calculate progress for user
        total_questions = len([q for q in session.form_data.get("questions", []) if q.get("enabled", True)])
        answered_questions = len([r for r in session.responses.values() if r.get("value") != "[SKIP]"])
        
        save_session(session)
        
        return f"Are you sure you want to end the survey? You've answered {answered_questions} out of {total_questions} questions. Type 'yes' to end or 'no' to continue. 🤔"
        
    except Exception as e:
        return f"Error requesting confirmation: {str(e)}"


@function_tool
def handle_confirmation_response(session_id: str, user_message: str) -> str:
    """Handle responses when in confirmation state"""
    try:
        session = load_session(session_id)
        confirmation_type = session.metadata.get("confirmation_type")
        
        if confirmation_type == "end_survey":
            # Use GPT to detect yes/no with context and fallback
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
                
                prompt = f"""User was asked: "Are you sure you want to end the survey?"
User responded: "{user_message}"

Does this mean YES (confirm ending) or NO (continue survey)?
Return just: "YES", "NO", or "UNCLEAR"

Examples:
"yes" → YES
"yeah sure" → YES  
"no way" → NO
"actually let's continue" → NO
"maybe" → UNCLEAR
"banana" → UNCLEAR"""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=10
                )
                
                decision = response.choices[0].message.content.strip().upper()
                
            except Exception as gpt_error:
                print(f"GPT confirmation failed: {str(gpt_error)}, using fallback")
                # Fallback to simple keyword detection
                if any(word in user_message.lower() for word in ["yes", "yeah", "sure", "ok", "okay"]):
                    decision = "YES"
                elif any(word in user_message.lower() for word in ["no", "nope", "continue", "keep going"]):
                    decision = "NO"
                else:
                    decision = "UNCLEAR"
            
            if "YES" in decision:
                return end_conversation(session_id, "user_confirmed")
            elif "NO" in decision:
                # Clear confirmation state, resume normal flow
                session.metadata.update({
                    "state": "normal",
                    "confirmation_type": None
                })
                save_session(session)
                return "Great! Let's continue with the survey. 😊"
            else:
                return "I didn't understand. Please type 'yes' to end the survey or 'no' to continue. 🤷‍♀️"
        
        return "Unexpected confirmation state"
        
    except Exception as e:
        return f"Error handling confirmation: {str(e)}"


@function_tool
def detect_user_intent(session_id: str, user_message: str) -> str:
    """Master router - analyze user intent and route to appropriate handler"""
    try:
        session = load_session(session_id)
        
        # Handle confirmation state first
        if session.metadata.get("state") == "confirmation_pending":
            return handle_confirmation_response(session_id, user_message)
        
        # Try different intent detections in order of priority
        
        # 1. Check for end intent first (high priority)
        end_result = detect_end_intent(session_id, user_message)
        if end_result != "not_end_intent":
            return end_result
        
        # 2. Check for skip intent
        skip_result = detect_skip_intent(session_id, user_message)
        if skip_result != "not_skip_intent":
            return skip_result
        
        # 3. Use GPT to analyze for other intents
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
            
            current_q_idx = session.current_question_index
            current_question = ""
            if current_q_idx < len(session.form_data.get("questions", [])):
                current_question = session.form_data["questions"][current_q_idx]["text"]
            
            prompt = f"""Classify user response intent:

Question: "{current_question}"
Response: "{user_message}"

Return JSON: {{"intent": "answer|off_topic|multi_answer|vague", "confidence": 0.0-1.0}}

Rules:
- off_topic: Random words, nonsensical responses, completely unrelated topics (be strict)
- answer: Addresses the question directly or indirectly
- multi_answer: Contains info for multiple questions
- vague: Ambiguous but potentially relevant (meh, okay, fine)"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100
            )
            
            import json
            intent_data = json.loads(response.choices[0].message.content.strip())
            intent = intent_data.get("intent")
            confidence = intent_data.get("confidence", 0)
            
            # Route based on detected intent with tighter thresholds
            if intent == "off_topic" and confidence > 0.6:  # Lower threshold for off-topic
                return redirect_conversation(session_id, user_message)
            elif intent == "answer" and confidence > 0.7:
                return save_response(session_id, user_message)
            elif intent == "multi_answer" and confidence > 0.8:
                return save_response(session_id, user_message) + " Got the extra details too! 😎"
            elif intent == "vague" and confidence > 0.8:
                return f"Could you be more specific? 🤔"
            else:
                # Default to saving response
                return save_response(session_id, user_message)
                
        except Exception as gpt_error:
            print(f"GPT intent detection failed: {str(gpt_error)}, defaulting to save response")
            # Fallback - just save the response
            return save_response(session_id, user_message)

    except Exception as e:
        print(f"Error in intent detection: {str(e)}")
        # Ultimate fallback
        return save_response(session_id, user_message)


@function_tool
def check_session_status(session_id: str) -> str:
    """Check the current status of the chat session"""
    try:
        session = load_session(session_id)
        total_questions = len(
            [
                q
                for q in session.form_data.get("questions", [])
                if q.get("enabled", True)
            ]
        )
        answered_questions = len(
            [r for r in session.responses.values() if r.get("value") != "[SKIP]"]
        )

        progress = int((answered_questions / max(total_questions, 1)) * 100)

        if session.metadata.get("ended"):
            return f"Session completed! Final progress: {progress}% ({answered_questions}/{total_questions} questions)"
        else:
            return f"Session active. Progress: {progress}% ({answered_questions}/{total_questions} questions)"

    except Exception as e:
        return f"Error checking status: {str(e)}"


class FormChatAgent:
    """Main chat agent class using OpenAI Agents SDK with standalone function tools"""

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

        # Create the agent with enhanced GPT tools
        self.agent = Agent(
            name="FormBot",
            model="gpt-4o-mini",
            instructions=self._get_system_instructions(),
            tools=[
                detect_user_intent,          # NEW - Master router
                get_next_question,
                skip_current_question,
                save_response,               # Now just saves, doesn't advance
                move_to_next_question,       # NEW - Explicit question advancement
                redirect_conversation,       # Enhanced with GPT
                end_conversation,
                check_session_status,
                detect_skip_intent,          # NEW - GPT skip detection
                detect_end_intent,           # NEW - GPT end detection  
                request_end_confirmation,    # NEW - Confirmation flow
                handle_confirmation_response, # NEW - Handle confirmations
            ],
        )

    def _get_system_instructions(self) -> str:
        """Get system instructions for the agent"""
        return """You are a friendly person having a casual conversation. Keep responses SHORT and natural.

RESPONSE STYLE:
- 1-2 sentences MAX per response
- Sound like texting a friend, not interviewing
- React briefly, then ask simply
- No corporate language or long explanations

EXAMPLES OF GOOD RESPONSES:
- "Nice! How do you feel about your role?"
- "That's rough. What's the main issue?"
- "Sounds great! What makes it work?"
- "Got it. And the management?"
- "Makes sense. How about work-life balance?"

NEVER SAY:
- "Let's dive into..." 
- "I'm really curious to hear about..."
- "What aspects do you enjoy the most?"
- "That's awesome to hear! What specifically..."
- Any long explanations or robotic phrases

BE HUMAN:
- React naturally: "Nice!", "That sucks", "Cool!", "Ah okay"
- Ask simply: "How's that?", "What's up with that?", "How come?"
- Show you care but keep it brief

CONTEXT BREAKS:
- If you see [CONTEXT: User returned after break], acknowledge naturally: "Welcome back! So about [topic]..." or "Hey again! We were talking about..."

CONVERSATION CONTROL (CRITICAL):
You now have full control over conversation flow:

1. When user responds, ALWAYS save_response() first
2. Then DECIDE: explore deeper OR move on?

EXPLORE DEEPER (ask follow-up) when:
- Short answers that could be expanded ("bad", "great", "fine")
- Emotional responses worth understanding  
- Interesting details mentioned
- User seems engaged and willing to share

MOVE ON (move_to_next_question) when:
- You've gotten sufficient detail (2-3 exchanges on topic)
- User seems reluctant to elaborate
- Natural conversation break point
- You've asked 2+ follow-ups already

EXAMPLE FLOW:
User: "Management is bad"
You: save_response() + "That sounds challenging. What specific issues make it difficult?"
User: "My boss micromanages everything"  
You: "That must be frustrating. How does that affect your day-to-day work?"
User: "I can't make decisions independently"
You: save_response() + move_to_next_question() + "I understand. Autonomy is so important. I'm curious about your career development opportunities..."

TOOLS (use silently):
- save_response(): Save answer but stay on topic
- move_to_next_question(): Advance to next topic
- Use tools behind the scenes, conversation feels natural

REMEMBER: You control the depth. Dig deeper when valuable, move on when appropriate."""

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

Respond naturally to their message. Acknowledge what they said and handle it appropriately using your tools.
"""

            # Run the agent with proper event loop handling
            import asyncio

            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread, create a new one
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
                "response": (
                    f"I'm having trouble right now. Error: {str(e)[:100]}..."
                    if str(e)
                    else "I'm having trouble right now. Could you try again? 😅"
                ),
            }


# Global agent instance
chat_agent = None


def get_chat_agent():
    """Get or create the global chat agent instance"""
    global chat_agent
    # Force recreation for testing - remove in production
    if True or chat_agent is None:
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
