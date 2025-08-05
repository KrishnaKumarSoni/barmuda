#!/usr/bin/env python3
"""Test exclamation mark handling specifically"""

import requests
import json

def test_exclamation_direct():
    """Test exclamation mark via direct Python requests (not curl)"""
    
    # Start session
    start_response = requests.post(
        "http://localhost:5000/api/chat/start",
        json={"form_id": "VhmJufviBBiuT1xUjypY", "device_id": "python_test_exclamation"}
    )
    
    if not start_response.ok:
        print(f"❌ Failed to start session: {start_response.text}")
        return
        
    session_data = start_response.json()
    session_id = session_data["session_id"]
    print(f"✅ Session started: {session_id}")
    
    # Test message with exclamation
    test_message = "I am done!"
    print(f"🔍 Testing message: '{test_message}'")
    
    message_response = requests.post(
        "http://localhost:5000/api/chat/message",
        json={"session_id": session_id, "message": test_message}
    )
    
    print(f"📊 Response status: {message_response.status_code}")
    print(f"📊 Response headers: {dict(message_response.headers)}")
    
    try:
        result = message_response.json()
        print(f"📊 Response JSON: {json.dumps(result, indent=2)}")
        
        if result.get("success"):
            print("✅ SUCCESS: Exclamation mark works via Python requests!")
        else:
            print(f"❌ FAILED: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"📊 Raw response: {message_response.text}")

if __name__ == "__main__":
    test_exclamation_direct()