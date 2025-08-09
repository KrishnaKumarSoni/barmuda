#!/usr/bin/env python3
"""
Quick test for debug output
"""

import requests
import random

BASE_URL = "https://barmuda.in"
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

# Fresh session
device_id = f"quick_debug_{random.randint(100000, 999999)}"

print("Starting session...")
start_response = requests.post(
    f"{BASE_URL}/api/chat/start",
    json={"form_id": FORM_ID, "device_id": device_id, "location": {"country": "US", "city": "Test"}},
    timeout=30
)

if start_response.status_code == 200:
    session_id = start_response.json().get("session_id")
    print(f"Session: {session_id}")
    
    print("Sending test message...")
    response = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={"session_id": session_id, "message": "test debug"},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data.get('response', 'No response')}")
        print(f"Keys: {list(data.keys())}")
        
        if 'debug_signature' in data:
            print(f"✅ SIGNATURE: {data['debug_signature']}")
        else:
            print("❌ NO SIGNATURE")
    else:
        print(f"Error: {response.status_code} - {response.text}")
else:
    print(f"Start failed: {start_response.status_code} - {start_response.text}")