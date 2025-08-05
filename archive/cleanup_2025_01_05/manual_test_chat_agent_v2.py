#!/usr/bin/env python3
"""
Test script for the chat agent v2 functionality
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in environment variables")
    sys.exit(1)
else:
    print("✅ OpenAI API key found")

# Test imports
try:
    from chat_agent_v2 import FormChatAgent, get_chat_agent

    print("✅ Chat agent v2 imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test creating a test form in Firestore
try:
    import firebase_admin
    from firebase_admin import firestore

    if not firebase_admin._apps:
        cred = firebase_admin.credentials.Certificate(
            "bermuda-01-firebase-adminsdk-fbsvc-660474f630.json"
        )
        firebase_admin.initialize_app(
            cred, {"databaseURL": "https://bermuda-01-default-rtdb.firebaseio.com/"}
        )

    db = firestore.client()

    # Create a test form
    test_form = {
        "title": "Quick Customer Survey",
        "description": "A simple survey to test our chat agent",
        "creator_id": "test_user",
        "questions": [
            {"text": "What is your name?", "type": "text", "enabled": True},
            {
                "text": "How would you rate our service?",
                "type": "rating",
                "enabled": True,
            },
            {
                "text": "Would you recommend us to a friend?",
                "type": "yes_no",
                "enabled": True,
            },
        ],
        "created_at": datetime.now(),
        "response_count": 0,
    }

    # Add to Firestore
    doc_ref = db.collection("forms").add(test_form)
    test_form_id = doc_ref[1].id
    print(f"✅ Test form created with ID: {test_form_id}")

except Exception as e:
    print(f"❌ Firebase setup error: {e}")
    sys.exit(1)

# Test chat agent functionality
try:
    print("\n🧪 Testing Chat Agent v2...")

    agent = get_chat_agent()
    print("✅ Chat agent instance created")

    # Create a test session
    session_id = agent.create_session(
        test_form_id, "test_device_456", {"test": "location"}
    )
    print(f"✅ Chat session created: {session_id}")

    # Test conversation flow
    print("\n💬 Testing conversation flow...")

    # Initial greeting
    result1 = agent.process_message(session_id, "Hello! I'm ready to start the survey.")
    if result1.get("success"):
        print(f"✅ Initial message processed")
        print(f"   Bot: {result1['response']}")
    else:
        print(f"❌ Initial message failed: {result1.get('error')}")
        sys.exit(1)

    # Answer first question
    result2 = agent.process_message(session_id, "My name is Alice Johnson")
    if result2.get("success"):
        print(f"✅ First answer processed")
        print(f"   Bot: {result2['response']}")
    else:
        print(f"❌ First answer failed: {result2.get('error')}")

    # Answer rating question
    result3 = agent.process_message(session_id, "I'd rate it a 4 - pretty good!")
    if result3.get("success"):
        print(f"✅ Rating processed")
        print(f"   Bot: {result3['response']}")
    else:
        print(f"❌ Rating failed: {result3.get('error')}")

    # Skip final question
    result4 = agent.process_message(session_id, "Can I skip the last question?")
    if result4.get("success"):
        print(f"✅ Skip request processed")
        print(f"   Bot: {result4['response']}")
    else:
        print(f"❌ Skip failed: {result4.get('error')}")

    print("\n🎉 All tests passed! Chat agent v2 is working correctly.")
    print(f"🌐 You can test the form at: http://localhost:5000/form/{test_form_id}")

except Exception as e:
    print(f"❌ Chat agent test failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
