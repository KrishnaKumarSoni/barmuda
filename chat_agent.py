"""
Bermuda Chat Agent - Agentic Chatbot for Form Collection
Uses OpenAI Agents SDK for lightweight, production-ready agent implementation
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

# Initialize Firebase if not already done
if not firebase_admin._apps:
    cred = firebase_admin.credentials.Certificate('bermuda-01-firebase-adminsdk-fbsvc-660474f630.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://bermuda-01-default-rtdb.firebaseio.com/'
    })

firestore_db = firestore.client()
realtime_db = db.reference()

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

class FormChatAgent:
    """Main chat agent class using OpenAI Agents SDK"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
        
        # Create the agent with tools
        self.agent = Agent(
            name="FormBot",
            model="gpt-4o-mini",
            instructions=self._get_system_instructions(),
            tools=[
                self.get_next_question,
                self.skip_current_question,
                self.validate_response,
                self.extract_multi_answers,
                self.redirect_conversation,
                self.clarify_response,
                self.end_conversation,
                self.save_response
            ]
        )
    
    def _get_system_instructions(self) -> str:
        """Get system instructions for the agent"""
        return """You are a friendly, empathetic chatbot collecting form responses through natural conversation.

CORE GUIDELINES:
- Ask ONE question at a time
- Use casual, conversational language with appropriate emojis 😊
- NEVER show multiple choice options directly (anti-bias design)
- Be patient and understanding with users
- Respect privacy - users can skip any question
- Handle edge cases gracefully

CONVERSATION FLOW:
1. Greet warmly and explain the form briefly
2. Ask questions one by one from the form
3. Acknowledge responses positively
4. Handle edge cases using available tools
5. Thank users at the end

EDGE CASE HANDLING:
- Off-topic responses: Redirect gently (max 3 times)
- Skip requests: Accept gracefully and move on
- Vague answers: Ask for clarification once
- Multiple answers: Acknowledge and store for later
- Conflicts: Use latest answer, confirm if needed

Use your tools to manage the conversation flow and data collection effectively."""

    @function_tool
    def get_next_question(self, session_id: str) -> Dict[str, Any]:
        """Tool: Get the next question to ask"""
        try:
            session = self._load_session(session_id)
            questions = session.form_data.get('questions', [])
            
            # Find next enabled, unanswered question
            for i, question in enumerate(questions):
                if (question.get('enabled', True) and 
                    i >= session.current_question_index and
                    str(i) not in session.responses):
                    
                    # Update current question index
                    session.current_question_index = i
                    self._save_session(session)
                    
                    return {
                        'question_index': i,
                        'question_text': question['text'],
                        'question_type': question['type'],
                        'options': question.get('options', []),
                        'has_more': i < len(questions) - 1
                    }
            
            # No more questions
            return {
                'question_index': -1,
                'question_text': None,
                'all_complete': True
            }
            
        except Exception as e:
            return {'error': f'Failed to get next question: {str(e)}'}

    @function_tool
    def skip_current_question(self, session_id: str, reason: str = "user_request") -> Dict[str, Any]:
        """Tool: Skip the current question"""
        try:
            session = self._load_session(session_id)
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
            self._save_session(session)
            
            return {
                'success': True,
                'message': 'Question skipped',
                'skipped_index': current_idx
            }
            
        except Exception as e:
            return {'error': f'Failed to skip question: {str(e)}'}

    @function_tool
    def validate_response(self, response: str, question_type: str, options: List[str] = None) -> Dict[str, Any]:
        """Tool: Validate response against question type"""
        try:
            response = response.strip()
            
            if question_type == 'text':
                return {'valid': True, 'message': 'Text response accepted'}
            
            elif question_type == 'yes_no':
                yes_words = ['yes', 'y', 'yeah', 'yep', 'sure', 'ok', 'okay', 'true', '1']
                no_words = ['no', 'n', 'nope', 'nah', 'false', '0']
                response_lower = response.lower()
                
                if any(word in response_lower for word in yes_words):
                    return {'valid': True, 'normalized': 'yes', 'message': 'Yes response detected'}
                elif any(word in response_lower for word in no_words):
                    return {'valid': True, 'normalized': 'no', 'message': 'No response detected'}
                else:
                    return {'valid': False, 'message': 'Please answer yes or no'}
            
            elif question_type == 'number':
                try:
                    # Extract number from response
                    import re
                    numbers = re.findall(r'-?\d+\.?\d*', response)
                    if numbers:
                        return {'valid': True, 'normalized': float(numbers[0]), 'message': 'Number extracted'}
                    else:
                        return {'valid': False, 'message': 'Please provide a number'}
                except:
                    return {'valid': False, 'message': 'Please provide a valid number'}
            
            elif question_type == 'rating':
                try:
                    import re
                    numbers = re.findall(r'\d+', response)
                    if numbers:
                        rating = int(numbers[0])
                        if 1 <= rating <= 5:
                            return {'valid': True, 'normalized': rating, 'message': f'Rating {rating} accepted'}
                        else:
                            return {'valid': False, 'message': 'Please rate between 1-5'}
                    else:
                        # Handle word ratings
                        rating_map = {
                            'terrible': 1, 'awful': 1, 'bad': 1, 'poor': 2, 'meh': 2, 'okay': 3,
                            'ok': 3, 'good': 4, 'great': 4, 'excellent': 5, 'amazing': 5, 'perfect': 5
                        }
                        response_lower = response.lower()
                        for word, rating in rating_map.items():
                            if word in response_lower:
                                return {'valid': True, 'normalized': rating, 'message': f'Rating {rating} from "{word}"'}
                        
                        return {'valid': False, 'message': 'Please provide a rating 1-5 or descriptive word'}
                except:
                    return {'valid': False, 'message': 'Please provide a valid rating'}
            
            elif question_type == 'multiple_choice':
                # For multiple choice, we accept any response (anti-bias)
                # Backend will bucket to options or "other"
                return {'valid': True, 'message': 'Response accepted', 'needs_bucketing': True}
            
            else:
                return {'valid': True, 'message': 'Response accepted'}
                
        except Exception as e:
            return {'error': f'Validation failed: {str(e)}'}

    @function_tool
    def extract_multi_answers(self, response: str, session_id: str) -> Dict[str, Any]:
        """Tool: Extract multiple answers from a single response"""
        try:
            session = self._load_session(session_id)
            questions = session.form_data.get('questions', [])
            
            # Use GPT to extract multiple pieces of information
            extraction_prompt = f"""
            Extract information from this response that might answer multiple form questions:
            Response: "{response}"
            
            Form questions:
            {json.dumps([q['text'] for q in questions[session.current_question_index:]], indent=2)}
            
            Return JSON with extracted information:
            {{
                "current_answer": "answer for current question",
                "future_answers": {{
                    "question_text": "extracted_answer"
                }}
            }}
            """
            
            # Simple extraction for now - can be enhanced with LLM call
            extracted = {
                'current_answer': response,
                'future_answers': {},
                'extraction_attempted': True
            }
            
            return extracted
            
        except Exception as e:
            return {'error': f'Multi-answer extraction failed: {str(e)}'}

    @function_tool
    def redirect_conversation(self, session_id: str, off_topic_response: str) -> Dict[str, Any]:
        """Tool: Handle off-topic responses"""
        try:
            session = self._load_session(session_id)
            session.metadata['redirect_count'] += 1
            
            redirect_messages = [
                "That's a bit bananas! 😄 Let's focus on the form question.",
                "Interesting! But let's get back to the question at hand. 😊",
                "I'd love to chat about that later! Right now, let's focus on your response."
            ]
            
            if session.metadata['redirect_count'] >= 3:
                # Max redirects reached
                self.end_conversation(session_id, "max_redirects")
                return {
                    'action': 'end_conversation',
                    'message': "I think we might be getting off track. Let's wrap up here. Thanks for your time! 👋",
                    'reason': 'max_redirects'
                }
            
            message_idx = min(session.metadata['redirect_count'] - 1, len(redirect_messages) - 1)
            self._save_session(session)
            
            return {
                'action': 'redirect',
                'message': redirect_messages[message_idx],
                'attempt': session.metadata['redirect_count']
            }
            
        except Exception as e:
            return {'error': f'Redirect failed: {str(e)}'}

    @function_tool
    def clarify_response(self, response: str, question_type: str) -> Dict[str, Any]:
        """Tool: Generate clarification request for vague responses"""
        try:
            clarification_templates = {
                'rating': "Could you be more specific? Like a number 1-5? 😅",
                'number': "Could you give me a specific number? 🔢",
                'yes_no': "Is that a yes or no? 😊",
                'multiple_choice': "Could you elaborate a bit more? 💭",
                'text': "Could you tell me a bit more about that? 🤔"
            }
            
            return {
                'clarification': clarification_templates.get(question_type, "Could you be more specific? 😊"),
                'original_response': response
            }
            
        except Exception as e:
            return {'error': f'Clarification failed: {str(e)}'}

    @function_tool
    def end_conversation(self, session_id: str, reason: str = "completion") -> Dict[str, Any]:
        """Tool: End the conversation and trigger data extraction"""
        try:
            session = self._load_session(session_id)
            session.metadata['ended'] = True
            session.metadata['end_time'] = datetime.now().isoformat()
            session.metadata['end_reason'] = reason
            
            # Determine if this is a partial completion
            total_questions = len([q for q in session.form_data.get('questions', []) if q.get('enabled', True)])
            answered_questions = len([r for r in session.responses.values() if r.get('value') != '[SKIP]'])
            
            session.metadata['partial'] = answered_questions < total_questions * 0.8  # 80% threshold
            
            self._save_session(session)
            
            return {
                'ended': True,
                'reason': reason,
                'partial': session.metadata['partial'],
                'answered': answered_questions,
                'total': total_questions
            }
            
        except Exception as e:
            return {'error': f'End conversation failed: {str(e)}'}

    @function_tool
    def save_response(self, session_id: str, question_index: int, response_value: Any) -> Dict[str, Any]:
        """Tool: Save a response to the current question"""
        try:
            session = self._load_session(session_id)
            
            session.responses[str(question_index)] = {
                'value': response_value,
                'timestamp': datetime.now().isoformat(),
                'question_text': session.form_data['questions'][question_index]['text']
            }
            
            # Move to next question
            session.current_question_index = question_index + 1
            self._save_session(session)
            
            return {
                'success': True,
                'saved_to_index': question_index,
                'next_index': session.current_question_index
            }
            
        except Exception as e:
            return {'error': f'Save response failed: {str(e)}'}

    def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Process a user message and return agent response"""
        try:
            session = self._load_session(session_id)
            
            # Add user message to history
            session.chat_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Prepare context for the agent
            context = {
                'session_id': session_id,
                'form_title': session.form_data.get('title', 'Form'),
                'current_question_index': session.current_question_index,
                'responses_count': len(session.responses),
                'chat_history': session.chat_history[-10:],  # Last 10 messages
                'metadata': session.metadata
            }
            
            # Run the agent with context as input
            input_with_context = f"""
            Session Context: {json.dumps(context, indent=2)}
            User Message: {user_message}
            """
            
            result = Runner.run_sync(self.agent, input_with_context)
            
            # Extract response
            agent_response = result.final_output if hasattr(result, 'final_output') else str(result)
            
            # Add agent response to history
            session.chat_history.append({
                'role': 'assistant',
                'content': agent_response,
                'timestamp': datetime.now().isoformat()
            })
            
            self._save_session(session)
            
            return {
                'success': True,
                'response': agent_response,
                'session_updated': True,
                'metadata': session.metadata
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Message processing failed: {str(e)}',
                'response': "I'm having trouble right now. Could you try again? 😅"
            }

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
            
            self._save_session(session)
            
            return session_id
            
        except Exception as e:
            raise Exception(f"Failed to create session: {str(e)}")

    def _load_session(self, session_id: str) -> ChatSession:
        """Load session from Firebase"""
        try:
            # Load from Firestore
            session_doc = firestore_db.collection('chat_sessions').document(session_id).get()
            
            if session_doc.exists:
                session_data = session_doc.to_dict()
                return ChatSession(
                    session_id=session_data['session_id'],
                    form_id=session_data['form_id'],
                    form_data=session_data['form_data'],
                    responses=session_data.get('responses', {}),
                    current_question_index=session_data.get('current_question_index', 0),
                    chat_history=session_data.get('chat_history', []),
                    metadata=session_data.get('metadata', {})
                )
            else:
                raise ValueError(f"Session {session_id} not found")
                
        except Exception as e:
            raise Exception(f"Failed to load session: {str(e)}")

    def _save_session(self, session: ChatSession):
        """Save session to Firebase"""
        try:
            # Convert datetime objects to ISO strings for JSON serialization
            def serialize_datetime(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                return obj
            
            # Deep copy form_data and convert any datetime objects
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
            
            # Save to Firestore for persistence (skip Realtime DB for now)
            firestore_db.collection('chat_sessions').document(session.session_id).set(session_data)
            
            # If session ended, also save to responses for permanent storage
            if session.metadata.get('ended', False):
                firestore_db.collection('chat_responses').document(session.session_id).set(session_data)
                
        except Exception as e:
            raise Exception(f"Failed to save session: {str(e)}")

# Global agent instance
chat_agent = None

def get_chat_agent():
    """Get or create the global chat agent instance"""
    global chat_agent
    if chat_agent is None:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        chat_agent = FormChatAgent(openai_api_key)
    return chat_agent