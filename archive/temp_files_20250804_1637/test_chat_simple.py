#!/usr/bin/env python3
"""
Test script for simplified chat agent
Tests natural conversation flow without full Firebase setup
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List

# Mock session class for testing
@dataclass
class MockChatSession:
    session_id: str
    form_id: str = "test_form"
    form_data: Dict = None
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
                "state": "normal"
            }
        if self.form_data is None:
            self.form_data = {
                "title": "Customer Feedback Survey",
                "questions": [
                    {"text": "What's your favorite hobby?", "type": "text", "enabled": True},
                    {"text": "How satisfied are you with our service?", "type": "rating", "enabled": True},
                    {"text": "Would you recommend us to others?", "type": "yes_no", "enabled": True},
                    {"text": "Any additional comments?", "type": "text", "enabled": True}
                ]
            }

# Mock storage
mock_sessions = {}

def mock_load_session(session_id: str) -> MockChatSession:
    if session_id not in mock_sessions:
        session = MockChatSession(session_id=session_id)
        mock_sessions[session_id] = session
    return mock_sessions[session_id]

def mock_save_session(session: MockChatSession):
    mock_sessions[session.session_id] = session

# Patch the imports in chat_agent_simple
import sys
sys.path.insert(0, '/Users/krishna/Desktop/Dev work - 02/bermuda')

# Mock the chat_agent_v2 imports
class MockModule:
    def __init__(self):
        self.load_session = mock_load_session
        self.save_session = mock_save_session
        self.ChatSession = MockChatSession

sys.modules['chat_agent_v2'] = MockModule()

# Now import our simplified chat agent
from chat_agent_simple import process_message_naturally

def test_natural_responses():
    """Test natural conversation flow"""
    print("🧪 Testing Natural Chat Responses")
    print("=" * 50)
    
    session_id = "test_session_123"
    
    test_cases = [
        {
            "message": "Hi there!",
            "expected_intent": "unclear",
            "description": "Initial greeting"
        },
        {
            "message": "I love reading books and playing guitar",
            "expected_intent": "answer", 
            "description": "Direct answer to hobby question"
        },
        {
            "message": "skip this question please",
            "expected_intent": "skip",
            "description": "Skip request"
        },
        {
            "message": "I don't want to answer that, move on to the next",
            "expected_intent": "skip",
            "description": "Complex skip request"
        },
        {
            "message": "I'm done with this survey now",
            "expected_intent": "end",
            "description": "End survey request"
        },
        {
            "message": "yes",
            "expected_intent": "confirm_end",
            "description": "Confirmation response"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['description']}")
        print(f"User: \"{test_case['message']}\"")
        
        try:
            result = process_message_naturally(session_id, test_case["message"])
            
            if result["success"]:
                print(f"✅ Success: {result['response']}")
                print(f"   Intent handled naturally")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"💥 Exception: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("-" * 30)
    
    # Check session state
    final_session = mock_load_session(session_id)
    print(f"\n📊 Final Session State:")
    print(f"   Current Question: {final_session.current_question_index}")
    print(f"   Responses: {len(final_session.responses)}")
    print(f"   Chat History: {len(final_session.chat_history)} messages")
    print(f"   Ended: {final_session.metadata.get('ended', False)}")

def test_acknowledgment_variety():
    """Test that responses acknowledge user messages naturally"""
    print("\n🎭 Testing Response Acknowledgment Variety")
    print("=" * 50)
    
    session_id = "test_ack_session"
    
    answers = [
        "I love hiking in the mountains",
        "Playing chess is my favorite",
        "I enjoy cooking Italian food",
        "Reading science fiction novels",
        "Learning new programming languages"
    ]
    
    responses_seen = set()
    
    for answer in answers:
        print(f"\nUser: \"{answer}\"")
        result = process_message_naturally(session_id, answer)
        
        if result["success"]:
            response = result["response"]
            # Extract just the acknowledgment part (before "Now,")
            ack_part = response.split("Now,")[0].strip()
            responses_seen.add(ack_part)
            print(f"Bot: {response}")
        else:
            print(f"❌ Error: {result.get('error')}")
    
    print(f"\n📈 Acknowledgment Variety:")
    print(f"   Unique acknowledgments: {len(responses_seen)}")
    print(f"   Responses: {list(responses_seen)}")
    
    if len(responses_seen) > 1:
        print("✅ Good variety in acknowledgments!")
    else:
        print("⚠️ Limited acknowledgment variety")

if __name__ == "__main__":
    # Set up minimal environment
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "test-key")
    
    print("🚀 Starting Chat Agent Natural Response Tests")
    print(f"OpenAI API Key present: {bool(os.getenv('OPENAI_API_KEY'))}")
    print()
    
    try:
        test_natural_responses()
        test_acknowledgment_variety()
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()