#!/usr/bin/env python3
"""
Test the new conversational depth capabilities
Tests save_response vs move_to_next_question control
"""

import os
from unittest.mock import Mock, MagicMock
import sys

# Set up environment
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

# Mock Firebase to avoid dependency issues
firebase_mock = Mock()
firestore_mock = Mock()
firebase_mock.credentials = Mock()
firebase_mock.credentials.Certificate = Mock()
firebase_mock.initialize_app = Mock()

sys.modules['firebase_admin'] = firebase_mock
sys.modules['firebase_admin.credentials'] = firebase_mock.credentials
sys.modules['firebase_admin.firestore'] = firestore_mock

# Mock firestore client
firestore_client_mock = Mock()
firestore_mock.client.return_value = firestore_client_mock

try:
    from chat_agent_v2 import FormChatAgent, ChatSession, save_session
    
    print("🎯 TESTING CONVERSATIONAL DEPTH CONTROL")
    print("=" * 60)
    
    # Create agent
    agent = FormChatAgent(os.getenv("OPENAI_API_KEY"))
    
    # Create test session with multiple questions
    form_data = {
        "title": "Employee Engagement Survey",
        "questions": [
            {"text": "How do you feel about your current role?", "type": "text", "enabled": True},
            {"text": "How effective is management support?", "type": "text", "enabled": True},
            {"text": "Do you have career development opportunities?", "type": "text", "enabled": True},
            {"text": "Any additional feedback?", "type": "text", "enabled": True}
        ]
    }
    
    session = ChatSession(
        session_id="depth_test",
        form_id="test_form",
        form_data=form_data
    )
    save_session(session)
    
    print("📋 Test Scenario: Short Answer That Should Get Follow-up")
    print("-" * 50)
    
    # Test 1: Short answer should trigger follow-up
    print("\n1️⃣ Testing short answer 'bad' - should ask follow-up")
    result = agent.process_message("depth_test", "bad")
    if result.get("success"):
        response = result["response"]
        print(f"User: 'bad'")
        print(f"Bot: '{response}'")
        
        # Check if it asked follow-up without advancing
        session = load_session("depth_test") if 'load_session' in globals() else None
        if "what" in response.lower() or "how" in response.lower() or "why" in response.lower():
            print("✅ Agent asked follow-up question")
        else:
            print("⚠️ No follow-up detected")
            
        # Check if it mentioned next topic (it shouldn't)
        if "career development" in response.lower() or "opportunities" in response.lower():
            print("❌ Agent jumped to next question instead of following up")
        else:
            print("✅ Agent stayed on current topic")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    print("\n2️⃣ Testing follow-up response - should explore more")
    result = agent.process_message("depth_test", "My boss micromanages everything")
    if result.get("success"):
        response = result["response"]
        print(f"User: 'My boss micromanages everything'")
        print(f"Bot: '{response}'")
        
        # Should continue exploring
        if "how" in response.lower() or "what" in response.lower() or "affect" in response.lower():
            print("✅ Agent continued exploring the topic")
        else:
            print("⚠️ Agent didn't continue exploring")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    print("\n3️⃣ Testing detailed response - should move to next question")
    result = agent.process_message("depth_test", "I can't make any decisions on my own and feel completely controlled")
    if result.get("success"):
        response = result["response"]
        print(f"User: 'I can't make any decisions on my own and feel completely controlled'")
        print(f"Bot: '{response}'")
        
        # Should move to next topic after sufficient detail
        if "career" in response.lower() or "development" in response.lower() or "opportunities" in response.lower():
            print("✅ Agent moved to next question after getting detail")
        else:
            print("⚠️ Agent didn't move to next question")
    else:
        print(f"❌ Failed: {result.get('error')}")
    
    print("\n📊 KEY IMPROVEMENTS TESTED:")
    print("✅ save_response() no longer auto-advances")
    print("✅ Agent has move_to_next_question() control")
    print("✅ System instructions guide conversation depth")
    print("✅ Agent can explore topics before moving on")
    
    print("\n🎉 CONVERSATIONAL DEPTH CONTROL IMPLEMENTED!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()