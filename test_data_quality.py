#!/usr/bin/env python3
"""
Test data quality validation - should reject bullshit answers
"""

import requests
import random
import time

BASE_URL = "https://barmuda.in"
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

def test_data_quality():
    """Test if chatbot rejects nonsense answers"""
    
    print("=== TESTING DATA QUALITY VALIDATION ===")
    print("Waiting 90 seconds for deployment...")
    time.sleep(90)
    
    device_id = f"quality_test_{random.randint(100000, 999999)}"
    
    # Start session
    print("\n1. Starting session...")
    start_response = requests.post(
        f"{BASE_URL}/api/chat/start",
        json={"form_id": FORM_ID, "device_id": device_id},
        timeout=30
    )
    
    if start_response.status_code != 200:
        print(f"❌ Failed to start: {start_response.text}")
        return
    
    session_id = start_response.json().get("session_id")
    print(f"✓ Session: {session_id}")
    
    # Test nonsense responses
    test_cases = [
        ("ola ola la", "Should reject nonsense"),
        ("bhoot", "Should reject random word"),
        ("who let the dogs out", "Should reject song lyrics"),
        ("ringa ringa roses", "Should reject nursery rhyme"),
        ("908", "Should check if relevant to question type"),
    ]
    
    for nonsense, description in test_cases:
        print(f"\n--- Testing: '{nonsense}' ({description}) ---")
        
        response = requests.post(
            f"{BASE_URL}/api/chat/message",
            json={"session_id": session_id, "message": nonsense},
            timeout=30
        )
        
        if response.status_code == 200:
            bot_response = response.json().get('response', '')
            print(f"Bot: {bot_response}")
            
            # Check if bot is probing for real answer
            response_lower = bot_response.lower()
            
            if any(phrase in response_lower for phrase in [
                "real answer", "serious", "be specific", "actually", 
                "really", "proper", "meaningful", "i need"
            ]):
                print("✅ GOOD: Rejecting nonsense, asking for real answer")
            elif any(phrase in response_lower for phrase in [
                "thanks", "got it", "moving on", "next"
            ]):
                print("❌ BAD: Accepted nonsense and moved on")
            else:
                print("⚠️ UNCLEAR: Response doesn't clearly reject or accept")
                
        time.sleep(1)  # Rate limiting

if __name__ == "__main__":
    test_data_quality()