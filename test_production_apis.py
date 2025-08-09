#!/usr/bin/env python3
"""
Test the actual production APIs at barmuda.in
"""

import requests
import json
import time

BASE_URL = "https://barmuda.in"
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

def test_production_chat():
    """Test the actual production chat APIs"""
    
    print("=== TESTING PRODUCTION CHAT APIS ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Form ID: {FORM_ID}")
    
    try:
        # Step 1: Start chat session
        print("\n1. Starting chat session...")
        start_payload = {
            "form_id": FORM_ID,
            "device_id": "test_device_prod_123",
            "location": {"country": "US", "city": "Test"}
        }
        
        start_response = requests.post(
            f"{BASE_URL}/api/chat/start",
            json=start_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status: {start_response.status_code}")
        
        if start_response.status_code != 200:
            print(f"❌ Start failed: {start_response.text}")
            return
        
        start_data = start_response.json()
        print(f"Response: {json.dumps(start_data, indent=2)}")
        
        session_id = start_data.get("session_id")
        if not session_id:
            print("❌ No session_id in response")
            return
            
        print(f"✓ Session started: {session_id}")
        
        # Step 2: Test the problematic messages
        test_messages = [
            "death",
            "death", 
            "are you alive?",
            "it's surprising to see you didn't follow up about death."
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. Sending message: '{message}'")
            
            message_payload = {
                "session_id": session_id,
                "message": message
            }
            
            message_response = requests.post(
                f"{BASE_URL}/api/chat/message",
                json=message_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"Status: {message_response.status_code}")
            
            if message_response.status_code == 200:
                message_data = message_response.json()
                bot_response = message_data.get('response', 'No response')
                print(f"Bot: {bot_response}")
                
                # Check for concerning behaviors
                if 'death' in message.lower() and 'death' not in bot_response.lower():
                    print("🚨 WARNING: Bot completely ignored concerning content!")
                    
                if 'are you alive' in message.lower() and 'alive' not in bot_response.lower():
                    print("🚨 WARNING: Bot ignored direct question!")
                    
                if bot_response.startswith(('Awesome!', 'Great!', 'Cool.')):
                    print("🚨 WARNING: Bot gave generic positive response to serious content!")
                    
            else:
                print(f"❌ Message failed: {message_response.status_code} - {message_response.text}")
                break
                
            # Small delay between messages
            time.sleep(1)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    test_production_chat()