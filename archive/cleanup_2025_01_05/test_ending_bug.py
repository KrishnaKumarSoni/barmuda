#!/usr/bin/env python3
"""
Test the ending confirmation bug fix
"""

import requests
import json
import time

BASE_URL = "https://barmuda.in"
# Using friend's form for testing
FORM_ID = "5fjcRD3YcYkK5o3LIDyT"

def test_ending_confirmation():
    """Test that ending requires confirmation"""
    print("🧪 TESTING ENDING CONFIRMATION BUG FIX")
    print("=" * 50)
    
    device_id = f"ending_test_{int(time.time())}"
    
    try:
        # Start session
        print("1️⃣ Starting session...")
        start_response = requests.post(
            f"{BASE_URL}/api/chat/start",
            json={"form_id": FORM_ID, "device_id": device_id},
            timeout=15
        )
        
        if not start_response.ok:
            print(f"❌ Failed to start: {start_response.status_code}")
            return False
            
        session_data = start_response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session started: {session_id}")
        print(f"🤖 Initial greeting: {session_data.get('greeting')}")
        
        # Answer a few questions
        messages = [
            "Hello",
            "It was pretty good", 
            "I liked the structure"
        ]
        
        for i, message in enumerate(messages, 1):
            print(f"\n{i+1}️⃣ 👤 Me: '{message}'")
            
            response = requests.post(
                f"{BASE_URL}/api/chat/message",
                json={"session_id": session_id, "message": message},
                timeout=15
            )
            
            if not response.ok:
                print(f"❌ Message failed: {response.status_code}")
                return False
            
            result = response.json()
            bot_response = result["response"]
            ended = result.get("ended", False)
            
            print(f"🤖 Bot: {bot_response}")
            print(f"📊 Ended: {ended}")
            
            if ended:
                print("❌ BUG: Conversation ended unexpectedly!")
                return False
        
        # Now try to end the conversation
        print(f"\n4️⃣ 👤 Me: 'I'm done now'")
        
        response = requests.post(
            f"{BASE_URL}/api/chat/message",
            json={"session_id": session_id, "message": "I'm done now"},
            timeout=15
        )
        
        if not response.ok:
            print(f"❌ End request failed: {response.status_code}")
            return False
        
        result = response.json()
        bot_response = result["response"]
        ended_after_request = result.get("ended", False)
        
        print(f"🤖 Bot: {bot_response}")
        print(f"📊 Ended after 'I'm done': {ended_after_request}")
        
        # Check if it's asking for confirmation (should NOT end yet)
        if ended_after_request:
            print("❌ BUG: Conversation ended without confirmation!")
            return False
        
        if "sure" not in bot_response.lower() and "stop" not in bot_response.lower():
            print("❌ BUG: Bot didn't ask for confirmation!")
            return False
        
        print("✅ Bot correctly asked for confirmation without ending")
        
        # Now confirm ending
        print(f"\n5️⃣ 👤 Me: 'yes I'm sure'")
        
        response = requests.post(
            f"{BASE_URL}/api/chat/message",
            json={"session_id": session_id, "message": "yes I'm sure"},
            timeout=15
        )
        
        if not response.ok:
            print(f"❌ Confirmation failed: {response.status_code}")
            return False
        
        result = response.json()
        bot_response = result["response"]
        ended_after_confirmation = result.get("ended", False)
        
        print(f"🤖 Bot: {bot_response}")
        print(f"📊 Ended after confirmation: {ended_after_confirmation}")
        
        # Now it should end
        if not ended_after_confirmation:
            print("❌ BUG: Conversation didn't end after confirmation!")
            return False
        
        print("✅ Bot correctly ended after confirmation")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ending_confirmation()
    print(f"\n{'='*50}")
    if success:
        print("🎉 ENDING CONFIRMATION BUG FIX SUCCESSFUL!")
        print("✅ Agent now properly asks for confirmation before ending")
        print("✅ Two-step ending process working correctly")
    else:
        print("❌ ENDING CONFIRMATION BUG STILL EXISTS")
        print("🔍 Check the agent's system prompt and tool usage")