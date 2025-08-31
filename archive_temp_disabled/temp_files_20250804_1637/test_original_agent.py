#!/usr/bin/env python3
"""
Test the original GPT-powered agent to make sure it works
"""

import os
from datetime import datetime

# Set up environment
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

try:
    # Test importing the agent
    from chat_agent_v2 import FormChatAgent, ChatSession
    
    print("✅ Successfully imported FormChatAgent")
    
    # Test creating the agent
    print("🔄 Creating agent...")
    agent = FormChatAgent(os.getenv("OPENAI_API_KEY"))
    print("✅ Agent created successfully")
    
    # Test creating a mock session
    print("🔄 Testing session creation...")
    
    # Mock form data
    form_data = {
        "title": "Test Survey",
        "questions": [
            {"text": "What's your favorite hobby?", "type": "text", "enabled": True},
            {"text": "How satisfied are you?", "type": "rating", "enabled": True}
        ]
    }
    
    # Create session manually for testing
    from chat_agent_v2 import ChatSession, save_session
    
    session = ChatSession(
        session_id="test_original_agent",
        form_id="test_form",
        form_data=form_data
    )
    
    save_session(session)
    print("✅ Session created and saved")
    
    # Test processing a message
    print("🔄 Testing message processing...")
    result = agent.process_message("test_original_agent", "I love reading books")
    
    if result.get("success"):
        print("✅ Message processed successfully!")
        print(f"Response: {result['response']}")
    else:
        print(f"❌ Message processing failed: {result.get('error')}")
        
    print("\n🎉 Original GPT-powered agent is working!")
    
except Exception as e:
    print(f"❌ Error testing original agent: {str(e)}")
    import traceback
    traceback.print_exc()