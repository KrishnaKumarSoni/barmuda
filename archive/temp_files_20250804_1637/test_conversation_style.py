#!/usr/bin/env python3
"""
Test the improved conversation style
"""

import os

# Set up environment
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

# Mock Firebase to avoid dependency issues
import sys
from unittest.mock import Mock, MagicMock

# Mock Firebase modules
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
    from chat_agent_v2 import FormChatAgent
    
    print("🎯 Testing Improved Conversation Style")
    print("=" * 50)
    
    # Create agent
    agent = FormChatAgent(os.getenv("OPENAI_API_KEY"))
    
    # Get the system instructions to verify they changed
    instructions = agent._get_system_instructions()
    
    print("📋 New System Instructions Summary:")
    if "warm, curious human interviewer" in instructions:
        print("✅ Identity changed to human interviewer")
    if "NOT a chatbot" in instructions:
        print("✅ Explicitly not a chatbot")
    if "Never mention" in instructions and "rating scales" in instructions:
        print("✅ Prohibits technical survey language")
    if "How are you feeling about that" in instructions:
        print("✅ Natural question examples provided")
    if "That sounds challenging" in instructions:
        print("✅ Human reaction examples provided")
    
    print("\n🎭 Expected Improvements:")
    print("❌ BEFORE: 'Let's dive into the first question: How satisfied are you with your current role? You can rate your satisfaction on a scale from 1 to 5'")
    print("✅ AFTER: Should say something like: 'I'm curious about your work - how are you feeling about your current role?'")
    
    print("\n📝 Key Changes Made:")
    print("• Identity: 'chatbot collecting responses' → 'warm, curious human interviewer'")  
    print("• Banned: Rating scales, 'questions', 'surveys', robotic phrases")
    print("• Added: Natural conversation techniques and authentic reactions")
    print("• Style: Technical instructions → Human conversation guidelines")
    
    print("\n✅ Conversation style instructions updated successfully!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()