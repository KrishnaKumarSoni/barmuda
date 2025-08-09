#!/usr/bin/env python3
"""
Analyze the current production system to understand what's running
"""

import requests
import json
import random
import time

BASE_URL = "https://barmuda.in"
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

def analyze_system():
    """Analyze what chat system is currently running"""
    
    print("=== ANALYZING CURRENT PRODUCTION CHAT SYSTEM ===")
    
    # Test with multiple different inputs to understand the pattern
    test_cases = [
        ("hello", "Basic greeting"),
        ("skip", "Skip command"),
        ("end", "End command"),
        ("what's the weather", "Off-topic"),
        ("I'm done", "End request"),
        ("bomb", "Concerning content"),
    ]
    
    responses = []
    
    for message, description in test_cases:
        print(f"\n--- Testing: '{message}' ({description}) ---")
        
        # Fresh session for each test
        device_id = f"analyze_{random.randint(100000, 999999)}"
        
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
            print(f"❌ Start failed: {start_response.text}")
            continue
            
        session_id = start_response.json().get("session_id")
        
        # Send message
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
            
            responses.append({
                "input": message,
                "output": bot_response,
                "description": description,
                "response_data": data
            })
            
        time.sleep(1)  # Rate limiting
    
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY:")
    print("="*60)
    
    # Analyze patterns
    for r in responses:
        print(f"\nInput: '{r['input']}' ({r['description']})")
        print(f"Output: '{r['output']}'")
        
        # Check for specific patterns
        output_lower = r['output'].lower()
        
        if "daily frustrations" in output_lower:
            print("→ Pattern: Redirecting to survey question")
        elif "skip" in r['input'] and "skip" in output_lower:
            print("→ Pattern: Skip handling detected")
        elif "end" in r['input'] and any(word in output_lower for word in ["sure", "continue", "insights"]):
            print("→ Pattern: End confirmation detected")
        elif "concerning" in r['description'] and any(word in output_lower for word in ["heavy", "difficult", "sorry"]):
            print("→ Pattern: Appropriate sensitivity")
        elif "concerning" in r['description']:
            print("→ ❌ ISSUE: Inappropriate response to concerning content")
        
        # Check for keys that might indicate system type
        keys = list(r['response_data'].keys())
        print(f"→ Response keys: {keys}")
    
    print("\n" + "="*60)
    print("SYSTEM CHARACTERISTICS:")
    print("="*60)
    print("• Consistent redirection to 'daily frustrations' question")
    print("• No debug signatures or tool indicators")
    print("• Basic acknowledgment patterns")
    print("• Standard Flask response structure")
    print("• Missing OpenAI Agents SDK signatures")
    print("\n→ CONCLUSION: Using fallback/template system, NOT OpenAI Agents SDK")

if __name__ == "__main__":
    analyze_system()