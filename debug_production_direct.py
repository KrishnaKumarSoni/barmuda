#!/usr/bin/env python3
"""
Direct test to see what happens when we try to import agents
"""

import requests
import json

# Test by triggering an error that would show us what's happening
def test_production_debug():
    """Force an error to see debug output"""
    
    # Send invalid session to trigger error handling
    response = requests.post(
        "https://barmuda.in/api/chat/message",
        json={
            "session_id": "debug_invalid_session_12345", 
            "message": "test debug"
        },
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Also try with valid form but invalid session
    response2 = requests.post(
        "https://barmuda.in/api/chat/start",
        json={
            "form_id": "INVALID_FORM_ID_DEBUG",
            "device_id": "debug_device"
        },
        timeout=30
    )
    
    print(f"\nStart Status: {response2.status_code}")
    print(f"Start Response: {response2.text}")

if __name__ == "__main__":
    test_production_debug()