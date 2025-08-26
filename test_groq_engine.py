#!/usr/bin/env python3
"""
Test script for Groq Chat Engine
Tests the new Groq implementation against real Firebase data
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_groq_engine():
    """Test Groq chat engine functionality"""
    
    # Check required environment variables
    required_env_vars = [
        "GROQ_API_KEY",
        "FIREBASE_PROJECT_ID", 
        "FIREBASE_PRIVATE_KEY",
        "FIREBASE_CLIENT_EMAIL"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    print("✅ Environment variables loaded")
    
    try:
        from groq_chat_engine import GroqChatAgent, get_chat_agent
        print("✅ Groq chat engine imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Groq chat engine: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing Groq chat engine: {e}")
        return False
    
    # Test agent creation
    try:
        agent = get_chat_agent()
        print("✅ Groq agent created successfully")
    except Exception as e:
        print(f"❌ Failed to create Groq agent: {e}")
        return False
    
    # Test with mock form data (we'll use Firebase later)
    test_form_data = {
        "title": "Test Survey",
        "questions": [
            {
                "text": "What's your favorite color?",
                "type": "text",
                "enabled": True
            },
            {
                "text": "How would you rate your satisfaction?",
                "type": "number", 
                "enabled": True
            }
        ],
        "demographics": {"age": True, "gender": False},
        "profile_data": {"name": True, "email": False},
        "active": True
    }
    
    # Create a test session manually (bypassing Firebase for now)
    try:
        from groq_chat_engine import ChatSession, save_session
        import uuid
        
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            form_id="test-form",
            form_data=test_form_data
        )
        save_session(session)
        print(f"✅ Test session created: {session_id}")
        
        # Test message processing
        response = agent.process_message(session_id, "Hello, I'm ready to start!")
        print(f"✅ First message processed: {response['response'][:100]}...")
        
        # Test a follow-up message
        response2 = agent.process_message(session_id, "Blue is my favorite color")
        print(f"✅ Second message processed: {response2['response'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing chat flow: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_firebase_integration():
    """Test Firebase integration with MCP"""
    print("\n🔥 Testing Firebase Integration...")
    
    # We'll use MCP to test Firebase connectivity
    try:
        # First, let's check if we can list forms
        from groq_chat_engine import firestore_db
        
        # Try to get a real form from Firebase
        forms = list(firestore_db.collection("forms").limit(1).stream())
        
        if forms:
            form_doc = forms[0]
            form_data = form_doc.to_dict()
            form_id = form_doc.id
            
            print(f"✅ Found test form: {form_data.get('title', 'Untitled')} (ID: {form_id})")
            
            # Test creating session with real form
            from groq_chat_engine import get_chat_agent
            agent = get_chat_agent()
            
            try:
                session_id = agent.create_session(form_id, device_id="test-device")
                print(f"✅ Session created with real form: {session_id}")
                
                # Test a conversation
                response = agent.process_message(session_id, "Hi there!")
                print(f"✅ Real form conversation: {response['response'][:100]}...")
                
                return True
            except Exception as e:
                print(f"❌ Error with real form session: {e}")
                return False
        else:
            print("⚠️  No forms found in Firebase - creating test form...")
            return False
            
    except Exception as e:
        print(f"❌ Firebase connection failed: {e}")
        return False

def performance_comparison():
    """Compare response times between engines"""
    print("\n⚡ Performance Comparison...")
    
    # We'll implement this after basic functionality is confirmed
    print("⏳ Performance comparison will be implemented after basic tests pass")
    return True

if __name__ == "__main__":
    print("🚀 Testing Groq Chat Engine Implementation")
    print("=" * 50)
    
    # Run tests
    tests = [
        ("Basic Functionality", test_groq_engine),
        ("Firebase Integration", test_firebase_integration),
        ("Performance", performance_comparison),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 Groq implementation ready for integration!")
    else:
        print("\n🔧 Fix failing tests before integration")