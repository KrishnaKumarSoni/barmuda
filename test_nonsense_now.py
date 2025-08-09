#!/usr/bin/env python3
"""
Quick test for nonsense rejection
"""

import requests
import random

BASE_URL = "https://barmuda.in"
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

device_id = f"nonsense_test_{random.randint(100000, 999999)}"

# Start session
start = requests.post(f"{BASE_URL}/api/chat/start", json={"form_id": FORM_ID, "device_id": device_id}, timeout=30)
session_id = start.json().get("session_id")
print(f"Session: {session_id}")

# Test with nonsense
test_inputs = [
    "ola ola la",
    "bhoot", 
    "who let the dogs out"
]

for nonsense in test_inputs:
    print(f"\n>>> User: {nonsense}")
    
    resp = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={"session_id": session_id, "message": nonsense},
        timeout=30
    )
    
    bot = resp.json().get('response', '')
    print(f"<<< Bot: {bot}")
    
    # Check response quality
    if any(word in bot.lower() for word in ["real", "serious", "specific", "actually", "need"]):
        print("✅ REJECTS nonsense")
    elif any(word in bot.lower() for word in ["thanks", "got it", "next", "moving"]):
        print("❌ ACCEPTS nonsense")
    else:
        print("⚠️ UNCLEAR")