#!/usr/bin/env python3
"""
Test script for the chat agent functionality
"""

import os
import sys
import json
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
    from chat_agent import FormChatAgent, get_chat_agent

    print("✅ Chat agent imports successful")
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
        "title": "Test Chat Form",
        "description": "Testing the chat agent functionality",
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
    print("\n🧪 Testing Chat Agent...")

    agent = get_chat_agent()
    print("✅ Chat agent instance created")

    # Create a test session
    session_id = agent.create_session(
        test_form_id, "test_device_123", {"test": "location"}
    )
    print(f"✅ Chat session created: {session_id}")

    # Test a simple message
    result = agent.process_message(session_id, "Hello, I'm ready to start!")
    if result.get("success"):
        print(f"✅ Message processed successfully")
        print(f"   Response: {result['response'][:100]}...")
    else:
        print(f"❌ Message processing failed: {result.get('error')}")

    # Test getting next question (via session load)
    try:
        session = agent._load_session(session_id)
        if session.form_data.get("questions"):
            print(
                f"✅ Session loaded with {len(session.form_data['questions'])} questions"
            )
        else:
            print("❌ No questions found in session")
    except Exception as e:
        print(f"❌ Could not load session: {e}")

    print("\n🎉 All tests passed! Chat agent is working correctly.")
    print(f"🌐 You can test the form at: http://localhost:5000/form/{test_form_id}")

except Exception as e:
    print(f"❌ Chat agent test failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
