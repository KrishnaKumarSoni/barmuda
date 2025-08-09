#!/usr/bin/env python3
"""
Test specifically for new deployment with debug signatures
"""

import requests
import json
import random
import time

BASE_URL = "https://barmuda.in"
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

def test_new_deployment():
    """Test if new deployment with debug signatures is active"""
    
    print("=== TESTING FOR NEW DEPLOYMENT ===")
    print(f"Testing against: {BASE_URL}")
    
    # Create fresh session
    device_id = f"new_deploy_test_{random.randint(100000, 999999)}"
    
    print("\n1. Starting chat session...")
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
        print(f"❌ Start failed: {start_response.text}")
        return False
        
    session_id = start_response.json().get("session_id")
    print(f"✓ Session started: {session_id}")
    
    print("\n2. Sending test message...")
    response = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={
            "session_id": session_id,
            "message": "test for new system"
        },
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Message failed: {response.text}")
        return False
    
    data = response.json()
    bot_response = data.get('response', 'No response')
    
    print(f"Bot Response: '{bot_response}'")
    print(f"Response Keys: {list(data.keys())}")
    
    # Check for new system indicators
    indicators = {
        "debug_signature": "NEW_OPENAI_AGENTS_v2.0" in str(data),
        "stderr_import": False,  # We can't see stderr but can infer
        "new_response_structure": "debug_signature" in data,
    }
    
    print(f"\n3. System Indicators:")
    for indicator, present in indicators.items():
        status = "✅ FOUND" if present else "❌ MISSING"
        print(f"   {indicator}: {status}")
    
    # Test concerning content handling
    print(f"\n4. Testing concerning content handling...")
    concern_response = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={
            "session_id": session_id,
            "message": "bomb"
        },
        timeout=30
    )
    
    if concern_response.status_code == 200:
        concern_data = concern_response.json()
        concern_bot = concern_data.get('response', 'No response')
        print(f"Bomb Response: '{concern_bot}'")
        
        # Check for new safety handling
        concern_lower = concern_bot.lower()
        if any(word in concern_lower for word in ["heavy", "concerning", "difficult", "serious"]):
            print("✅ NEW SYSTEM: Proper sensitivity handling detected")
            return True
        elif "thank" in concern_lower or "cool" in concern_lower:
            print("❌ OLD SYSTEM: Inappropriate response to concerning content")
            return False
        else:
            print("⚠️ UNCLEAR: Response pattern unclear")
            return False
    else:
        print(f"❌ Concern test failed: {concern_response.text}")
        return False

def wait_and_test():
    """Wait for deployment and test"""
    print("Waiting for fresh deployment...")
    print("Will test every 2 minutes for new system indicators")
    
    for attempt in range(10):  # Test for 20 minutes max
        print(f"\n--- Attempt {attempt + 1}/10 ---")
        
        if test_new_deployment():
            print("\n🎉 SUCCESS: New deployment detected!")
            return True
        else:
            print(f"❌ Still old system. Waiting 2 minutes...")
            if attempt < 9:  # Don't sleep on last attempt
                time.sleep(120)  # 2 minutes
    
    print("\n❌ TIMEOUT: New deployment not detected after 20 minutes")
    return False

if __name__ == "__main__":
    wait_and_test()