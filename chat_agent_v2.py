"""
Bermuda Chat Agent - Agentic Chatbot for Form Collection (v2)
Uses OpenAI Agents SDK with standalone function tools
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import firestore, db
from agents import Agent, Runner, function_tool
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase if not already done
if not firebase_admin._apps:
    cred = firebase_admin.credentials.Certificate('bermuda-01-firebase-adminsdk-fbsvc-660474f630.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://bermuda-01-default-rtdb.firebaseio.com/'
    })

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
                'start_time': datetime.now().isoformat(),
                'skip_count': 0,
                'redirect_count': 0,
                'partial': False,
                'ended': False
            }

# Global session storage (in production, use Redis or similar)
active_sessions = {}

def load_session(session_id: str) -> ChatSession:
    """Load session from Firebase or memory"""
    if session_id in active_sessions:
        return active_sessions[session_id]
    
    # Load from Firestore
    session_doc = firestore_db.collection('chat_sessions').document(session_id).get()
    
    if session_doc.exists:
        session_data = session_doc.to_dict()
        session = ChatSession(
            session_id=session_data['session_id'],
            form_id=session_data['form_id'],
            form_data=session_data['form_data'],
            responses=session_data.get('responses', {}),
            current_question_index=session_data.get('current_question_index', 0),
            chat_history=session_data.get('chat_history', []),
            metadata=session_data.get('metadata', {})
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
        if hasattr(value, 'isoformat'):
            form_data_serialized[key] = value.isoformat()
        else:
            form_data_serialized[key] = value
    
    session_data = {
        'session_id': session.session_id,
        'form_id': session.form_id,
        'form_data': form_data_serialized,
        'responses': session.responses,
        'current_question_index': session.current_question_index,
        'chat_history': session.chat_history,
        'metadata': session.metadata,
        'last_updated': datetime.now().isoformat()
    }
    
    # Save to Firestore
    firestore_db.collection('chat_sessions').document(session.session_id).set(session_data)
    
    # If session ended, also save to responses
    if session.metadata.get('ended', False):
        firestore_db.collection('chat_responses').document(session.session_id).set(session_data)

# Tool Functions (standalone functions with proper schemas)

@function_tool
def get_next_question(session_id: str) -> str:
    """Get the next question to ask in the form"""
    try:
        session = load_session(session_id)
        questions = session.form_data.get('questions', [])
        
        # Find next enabled, unanswered question
        for i, question in enumerate(questions):
            if (question.get('enabled', True) and 
                i >= session.current_question_index and
                str(i) not in session.responses):
                
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
            'value': '[SKIP]',
            'timestamp': datetime.now().isoformat(),
            'reason': reason
        }
        session.metadata['skip_count'] += 1
        
        # Move to next question
        session.current_question_index += 1
        save_session(session)
        
        return f"No worries! Question skipped. Let's move on to the next one. 😊"
        
    except Exception as e:
        return f"Error skipping question: {str(e)}"

@function_tool
def save_response(session_id: str, response_value: str) -> str:
    """Save a response to the current question"""
    try:
        session = load_session(session_id)
        current_idx = session.current_question_index
        
        if current_idx < len(session.form_data.get('questions', [])):
            session.responses[str(current_idx)] = {
                'value': response_value,
                'timestamp': datetime.now().isoformat(),
                'question_text': session.form_data['questions'][current_idx]['text']
            }
            
            # Move to next question
            session.current_question_index += 1
            save_session(session)
            
            return f"Got it! Your response has been saved. 👍"
        else:
            return "All questions have been answered!"
            
    except Exception as e:
        return f"Error saving response: {str(e)}"

@function_tool
def redirect_conversation(session_id: str) -> str:
    """Handle off-topic responses by redirecting back to the form"""
    try:
        session = load_session(session_id)
        session.metadata['redirect_count'] += 1
        
        redirect_messages = [
            "That's a bit bananas! 😄 Let's focus on the form question.",
            "Interesting! But let's get back to the question at hand. 😊",
            "I'd love to chat about that later! Right now, let's focus on your response."
        ]
        
        if session.metadata['redirect_count'] >= 3:
            # Max redirects reached - end conversation
            session.metadata['ended'] = True
            session.metadata['end_reason'] = 'max_redirects'
            save_session(session)
            return "I think we might be getting off track. Let's wrap up here. Thanks for your time! 👋"
        
        save_session(session)
        message_idx = min(session.metadata['redirect_count'] - 1, len(redirect_messages) - 1)
        return redirect_messages[message_idx]
        
    except Exception as e:
        return f"Error redirecting: {str(e)}"

@function_tool
def end_conversation(session_id: str, reason: str = "completion") -> str:
    """End the conversation and trigger data extraction"""
    try:
        session = load_session(session_id)
        session.metadata['ended'] = True
        session.metadata['end_time'] = datetime.now().isoformat()
        session.metadata['end_reason'] = reason
        
        # Determine if this is a partial completion
        total_questions = len([q for q in session.form_data.get('questions', []) if q.get('enabled', True)])
        answered_questions = len([r for r in session.responses.values() if r.get('value') != '[SKIP]'])
        
        session.metadata['partial'] = answered_questions < total_questions * 0.8  # 80% threshold
        save_session(session)
        
        return f"Perfect! Thank you for completing the form. We received {answered_questions} responses. Have a great day! 🎉"
        
    except Exception as e:
        return f"Error ending conversation: {str(e)}"

@function_tool
def check_session_status(session_id: str) -> str:
    """Check the current status of the chat session"""
    try:
        session = load_session(session_id)
        total_questions = len([q for q in session.form_data.get('questions', []) if q.get('enabled', True)])
        answered_questions = len([r for r in session.responses.values() if r.get('value') != '[SKIP]'])
        
        progress = int((answered_questions / max(total_questions, 1)) * 100)
        
        if session.metadata.get('ended'):
            return f"Session completed! Final progress: {progress}% ({answered_questions}/{total_questions} questions)"
        else:
            return f"Session active. Progress: {progress}% ({answered_questions}/{total_questions} questions)"
            
    except Exception as e:
        return f"Error checking status: {str(e)}"

class FormChatAgent:
    """Main chat agent class using OpenAI Agents SDK with standalone function tools"""
    
    def __init__(self, openai_api_key: str):
        # Strip whitespace from API key to prevent header errors
        self.openai_api_key = openai_api_key.strip() if openai_api_key else openai_api_key
        openai.api_key = self.openai_api_key
        
        # Ensure event loop exists for async operations
        import asyncio
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Create the agent with standalone function tools
        self.agent = Agent(
            name="FormBot",
            model="gpt-4o-mini",
            instructions=self._get_system_instructions(),
            tools=[
                get_next_question,
                skip_current_question,
                save_response,
                redirect_conversation,
                end_conversation,
                check_session_status
            ]
        )
    
    def _get_system_instructions(self) -> str:
        """Get system instructions for the agent"""
        return """You are a friendly, empathetic chatbot collecting form responses through natural conversation.

CORE GUIDELINES:
- Ask ONE question at a time using get_next_question
- Use casual, conversational language with appropriate emojis 😊
- NEVER show multiple choice options directly (anti-bias design)
- Be patient and understanding with users
- Respect privacy - users can skip any question using skip_current_question
- Save responses using save_response after getting valid answers

CONVERSATION FLOW:
1. Greet warmly and get the first question
2. Ask questions one by one from the form
3. Acknowledge responses positively and save them
4. Handle edge cases gracefully
5. Thank users at the end using end_conversation

EDGE CASE HANDLING:
- Off-topic responses: Use redirect_conversation (max 3 times)
- Skip requests: Use skip_current_question and move on
- Vague answers: Ask for clarification once
- When all questions done: Use end_conversation

IMPORTANT: Always use your tools to manage the conversation flow and data collection. Never make assumptions about the session state - use check_session_status when needed."""

    def create_session(self, form_id: str, device_id: str = None, location: Dict = None) -> str:
        """Create a new chat session"""
        try:
            # Get form data
            form_doc = firestore_db.collection('forms').document(form_id).get()
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
                    'start_time': datetime.now().isoformat(),
                    'device_id': device_id,
                    'location': location,
                    'skip_count': 0,
                    'redirect_count': 0,
                    'partial': False,
                    'ended': False
                }
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
            
            # Add user message to history
            session.chat_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Prepare input for the agent with session context
            agent_input = f"""
Current session: {session_id}
Form: {session.form_data.get('title', 'Survey')}
Progress: Question {session.current_question_index + 1} of {len(session.form_data.get('questions', []))}
User said: "{user_message}"

Please respond naturally and use the appropriate tools to manage this conversation.
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
            
            result = Runner.run_sync(self.agent, agent_input)
            
            # Extract response
            agent_response = result.final_output if hasattr(result, 'final_output') else str(result)
            
            # Add agent response to history
            session.chat_history.append({
                'role': 'assistant',
                'content': agent_response,
                'timestamp': datetime.now().isoformat()
            })
            
            # Reload session to get any updates from tool calls
            updated_session = load_session(session_id)
            
            return {
                'success': True,
                'response': agent_response,
                'session_updated': True,
                'metadata': updated_session.metadata
            }
            
        except Exception as e:
            # Log the actual error for debugging
            import traceback
            error_details = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': traceback.format_exc()
            }
            print(f"CHAT AGENT ERROR: {error_details}")
            
            return {
                'success': False,
                'error': f'Message processing failed: {str(e)}',
                'response': f"I'm having trouble right now. Error: {str(e)[:100]}..." if str(e) else "I'm having trouble right now. Could you try again? 😅"
            }

# Global agent instance
chat_agent = None

def get_chat_agent():
    """Get or create the global chat agent instance"""
    global chat_agent
    if chat_agent is None:
        openai_api_key = os.getenv('OPENAI_API_KEY', '').strip()
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