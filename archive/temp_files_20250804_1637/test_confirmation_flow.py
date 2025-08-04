#!/usr/bin/env python3
"""
Test confirmation flow specifically
"""

import os
import sys
sys.path.insert(0, '/Users/krishna/Desktop/Dev work - 02/bermuda')

# Mock the chat_agent_v2 imports
from test_chat_simple import MockChatSession, mock_load_session, mock_save_session

class MockModule:
    def __init__(self):
        self.load_session = mock_load_session
        self.save_session = mock_save_session
        self.ChatSession = MockChatSession

sys.modules['chat_agent_v2'] = MockModule()

from chat_agent_simple import process_message_naturally

def test_confirmation_flow():
    """Test the full confirmation flow"""
    print("🔄 Testing Confirmation Flow")
    print("=" * 50)
    
    session_id = "test_confirm_session"
    
    # Step 1: Answer first question
    print("\n1️⃣  Answering first question")
    result = process_message_naturally(session_id, "I love reading")
    print(f"User: I love reading")
    print(f"Bot: {result['response']}")
    
    # Step 2: Request to end survey
    print("\n2️⃣  Requesting to end survey")
    result = process_message_naturally(session_id, "I'm done, don't want to continue")
    print(f"User: I'm done, don't want to continue")
    print(f"Bot: {result['response']}")
    
    # Check if we're in confirmation state
    session = mock_load_session(session_id)
    print(f"   State: {session.metadata.get('state')}")
    print(f"   Ended: {session.metadata.get('ended')}")
    
    # Step 3: Decline to end (continue survey)
    print("\n3️⃣  Declining to end (continue survey)")
    result = process_message_naturally(session_id, "no, let's continue")
    print(f"User: no, let's continue")
    print(f"Bot: {result['response']}")
    
    # Check state after declining
    session = mock_load_session(session_id)
    print(f"   State: {session.metadata.get('state')}")
    print(f"   Ended: {session.metadata.get('ended')}")
    
    # Step 4: Answer next question
    print("\n4️⃣  Continuing with next question")
    result = process_message_naturally(session_id, "Very satisfied")
    print(f"User: Very satisfied")
    print(f"Bot: {result['response']}")
    
    # Step 5: Request to end again
    print("\n5️⃣  Requesting to end survey again")
    result = process_message_naturally(session_id, "I want to stop now")
    print(f"User: I want to stop now")
    print(f"Bot: {result['response']}")
    
    # Step 6: Confirm ending
    print("\n6️⃣  Confirming to end survey")
    result = process_message_naturally(session_id, "yes, end it")
    print(f"User: yes, end it")
    print(f"Bot: {result['response']}")
    
    # Final state check
    session = mock_load_session(session_id)
    print(f"\n📊 Final State:")
    print(f"   State: {session.metadata.get('state')}")
    print(f"   Ended: {session.metadata.get('ended')}")
    print(f"   Responses: {len(session.responses)}")
    print(f"   Current Question: {session.current_question_index}")

def test_edge_cases():
    """Test edge cases in confirmation"""
    print("\n\n🎯 Testing Edge Cases")
    print("=" * 50)
    
    session_id = "test_edge_session"
    
    # Test unclear confirmation response
    print("\n1️⃣  Unclear confirmation response")
    process_message_naturally(session_id, "Some hobby")
    result = process_message_naturally(session_id, "I'm done")
    print(f"User: I'm done")
    print(f"Bot: {result['response']}")
    
    result = process_message_naturally(session_id, "maybe")
    print(f"User: maybe")
    print(f"Bot: {result['response']}")
    
    # Test multiple skip requests
    print("\n2️⃣  Multiple skip requests")
    session_id2 = "test_skip_session"
    result = process_message_naturally(session_id2, "skip")
    print(f"User: skip")
    print(f"Bot: {result['response']}")
    
    result = process_message_naturally(session_id2, "skip this too")
    print(f"User: skip this too")
    print(f"Bot: {result['response']}")

if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "test-key")
    
    try:
        test_confirmation_flow()
        test_edge_cases()
        print("\n✅ All confirmation tests completed!")
        
    except Exception as e:
        print(f"\n💥 Confirmation test failed: {str(e)}")
        import traceback
        traceback.print_exc()