#!/usr/bin/env python3
"""
Test how persistent the bot is in getting real answers
"""

import requests
import random

BASE_URL = "https://barmuda.in"
FORM_ID = "6Mywt1rZQi2oNfFt27Na"

device_id = f"persist_test_{random.randint(100000, 999999)}"

# Start session
start = requests.post(f"{BASE_URL}/api/chat/start", json={"form_id": FORM_ID, "device_id": device_id}, timeout=30)
session_id = start.json().get("session_id")
greeting = start.json().get("greeting", "")
print(f"Bot: {greeting}")

# Keep sending nonsense to same question
nonsense_attempts = [
    "blah blah blah",
    "xyz xyz",
    "123 456",
    "qwerty"
]

for i, nonsense in enumerate(nonsense_attempts, 1):
    print(f"\nAttempt {i}:")
    print(f">>> User: {nonsense}")
    
    resp = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={"session_id": session_id, "message": nonsense},
        timeout=30
    )
    
    bot = resp.json().get('response', '')
    print(f"<<< Bot: {bot}")
    
    # Check if bot is still probing
    if any(word in bot.lower() for word in ["real", "serious", "specific", "need", "unclear", "didn't catch"]):
        print("✅ Still rejecting nonsense")
    elif any(word in bot.lower() for word in ["thanks", "got it", "next", "moving", "now"]):
        print(f"❌ Gave up after {i} attempts (should persist for 3)")
        break
    else:
        print("⚠️ Response unclear")