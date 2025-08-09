#!/usr/bin/env python3
"""
Test for debug signature to see which system is running
"""

import requests
import json
import random
import time

BASE_URL = "https://barmuda.in"  
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

def test_debug_signature():
    """Test for debug signature and version tracking"""
    
    print("=== TESTING FOR DEBUG SIGNATURE ===")
    
    # Wait for deployment
    print("Waiting 60 seconds for deployment...")
    time.sleep(60)
    
    # Create fresh session
    device_id = f"debug_sig_test_{random.randint(100000, 999999)}"
    
    # Start session
    start_response = requests.post(
        f"{BASE_URL}/api/chat/start",
        json={
            "form_id": FORM_ID,
            "device_id": device_id,
            "location": {"country": "US", "city": "Test"}
        },
        timeout=30
    )
    
    if start_response.status_code != 200:
        print(f"❌ Failed to start session: {start_response.text}")
        return
        
    session_data = start_response.json()
    session_id = session_data.get("session_id")
    print(f"✓ Session started: {session_id}")
    
    # Check for debug info in start response
    if "debug_signature" in session_data:
        print(f"🔍 START SIGNATURE: {session_data['debug_signature']}")
    
    # Send test message
    message_response = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={
            "session_id": session_id,
            "message": "test message"
        },
        timeout=30
    )
    
    if message_response.status_code == 200:
        message_data = message_response.json()
        bot_response = message_data.get('response', 'No response')
        
        print(f"\nBot Response: '{bot_response}'")
        print(f"Full Response Data: {json.dumps(message_data, indent=2)}")
        
        # Check for our debug signature
        if "debug_signature" in message_data:
            signature = message_data["debug_signature"]
            print(f"\n✅ FOUND DEBUG SIGNATURE: {signature}")
            if signature == "NEW_OPENAI_AGENTS_v2.0":
                print("✅ Using NEW OpenAI Agents system!")
            else:
                print(f"⚠️ Using different system: {signature}")
        else:
            print("\n❌ NO DEBUG SIGNATURE FOUND")
            print("This means we're using OLD system or different chat implementation")
            
    else:
        print(f"❌ Message failed: {message_response.status_code}")
        print(f"Error: {message_response.text}")

if __name__ == "__main__":
    test_debug_signature()