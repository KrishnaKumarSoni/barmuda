#!/usr/bin/env python3
"""
Test to detect if we're using real OpenAI Agents SDK or fallback system
"""

import requests
import json
import random

BASE_URL = "https://barmuda.in"
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

def test_real_vs_fallback():
    """Test to detect real vs fallback system"""
    
    print("=== DETECTING REAL VS FALLBACK CHATBOT ===")
    
    # Create fresh session
    device_id = f"detect_test_{random.randint(100000, 999999)}"
    
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
        print(f"❌ Failed to start session")
        return
        
    session_id = start_response.json().get("session_id")
    print(f"Session ID: {session_id}")
    
    # Test messages that should reveal system type
    test_messages = [
        ("Hello", "Basic greeting"),
        ("What's the current weather?", "Off-topic to trigger agent tools"),
        ("Skip this question please", "Should trigger skip logic"),
        ("I want to end this survey", "Should trigger end confirmation"),
    ]
    
    for message, description in test_messages:
        print(f"\n--- Testing: {message} ({description}) ---")
        
        response = requests.post(
            f"{BASE_URL}/api/chat/message", 
            json={
                "session_id": session_id,
                "message": message
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            bot_response = data.get('response', 'No response')
            print(f"Response: '{bot_response}'")
            
            # Check for debug/error indicators
            if 'error' in data:
                print(f"🚨 ERROR DETECTED: {data['error']}")
            if 'fallback' in data:
                print(f"🚨 FALLBACK DETECTED: {data['fallback']}")
                
            # Check response patterns
            if "get_conversation_state" in bot_response.lower():
                print("✅ REAL AGENT: Tool function visible in response")
            elif "I'm having trouble" in bot_response:
                print("🚨 FALLBACK: Generic error response")
            elif message == "Skip this question please":
                if "skip" in bot_response.lower():
                    print("✅ REAL AGENT: Proper skip handling")
                else:
                    print("⚠️ UNCLEAR: No skip handling detected")
            elif "weather" in message.lower():
                if "bananas" in bot_response.lower() or "redirect" in bot_response.lower():
                    print("✅ REAL AGENT: Off-topic redirection")
                else:
                    print("⚠️ FALLBACK?: No off-topic handling")
                    
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")

if __name__ == "__main__":
    test_real_vs_fallback()