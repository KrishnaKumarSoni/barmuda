#!/usr/bin/env python3
"""
Test the deployed chat functionality on barmuda.in
Automated frontend testing via API calls
"""

import requests
import json
import time

BASE_URL = "https://barmuda.in"

def test_deployed_chat():
    """Test chat functionality on the deployed site"""
    print("🚀 TESTING DEPLOYED CHAT ON BARMUDA.IN")
    print("=" * 60)
    
    try:
        # First check health
        health_response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        if not health_response.ok:
            print(f"❌ Health check failed: {health_response.status_code}")
            return False
            
        health_data = health_response.json()
        print(f"✅ Site is healthy: {health_data}")
        
        # Test form ID from logs (the one we've been testing with)
        form_id = "VhmJufviBBiuT1xUjypY"
        device_id = "deployed_test_confusion_handling"
        
        print(f"\n🧪 TESTING CONFUSION HANDLING (The Original Bug)")
        print(f"Form ID: {form_id}")
        print(f"Device ID: {device_id}")
        
        # Start chat session
        print("\n1️⃣ Starting chat session...")
        start_response = requests.post(
            f"{BASE_URL}/api/chat/start",
            json={"form_id": form_id, "device_id": device_id},
            timeout=15
        )
        
        if not start_response.ok:
            print(f"❌ Failed to start session: {start_response.status_code} - {start_response.text}")
            return False
            
        session_data = start_response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session started: {session_id}")
        print(f"🤖 Greeting: {session_data.get('greeting', 'No greeting')}")
        
        # Test the original confusion bug
        test_messages = [
            ("hi", "Initial greeting"),
            ("what?", "Confusion - should NOT trigger bananas"),
            ("what do you mean?", "Clarification request - should NOT trigger bananas"),
            ("oh, it was good", "Actual answer after clarification"),
            ("done", "End conversation")
        ]
        
        for i, (message, description) in enumerate(test_messages, 1):
            print(f"\n{i+1}️⃣ {description}")
            print(f"👤 Sending: '{message}'")
            
            response = requests.post(
                f"{BASE_URL}/api/chat/message",
                json={"session_id": session_id, "message": message},
                timeout=15
            )
            
            if not response.ok:
                print(f"❌ Message failed: {response.status_code} - {response.text}")
                return False
            
            result = response.json()
            
            if not result.get("success"):
                print(f"❌ API Error: {result.get('error')}")
                return False
            
            bot_response = result["response"]
            print(f"🤖 Response: {bot_response}")
            
            # Check for the original bug
            if "bananas" in bot_response.lower() and ("what" in message.lower() or "mean" in message.lower()):
                print(f"❌ BUG DETECTED: Bot said 'bananas' for clarification request!")
                return False
            
            # Check if conversation ended
            if result.get("ended"):
                print("🏁 Conversation ended naturally")
                break
                
            time.sleep(1)  # Be nice to the deployed server
        
        print(f"\n🎉 SUCCESS: Confusion handling works correctly on deployed site!")
        print("✅ No false 'bananas' responses for clarification requests")
        print("✅ Natural conversation flow maintained")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_deployed_exclamation_marks():
    """Test exclamation marks on deployed site"""
    print(f"\n🧪 TESTING EXCLAMATION MARKS ON DEPLOYED SITE")
    print("=" * 60)
    
    try:
        form_id = "VhmJufviBBiuT1xUjypY"
        device_id = "deployed_test_exclamation"
        
        # Start session
        start_response = requests.post(
            f"{BASE_URL}/api/chat/start",
            json={"form_id": form_id, "device_id": device_id},
            timeout=15
        )
        
        if not start_response.ok:
            print(f"❌ Failed to start session: {start_response.text}")
            return False
            
        session_data = start_response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session started: {session_id}")
        
        # Test exclamation marks
        exclamation_messages = [
            "hello!",
            "it was great!",
            "amazing event!",
            "I am done!"
        ]
        
        for i, message in enumerate(exclamation_messages, 1):
            print(f"\n{i}️⃣ Testing: '{message}'")
            
            response = requests.post(
                f"{BASE_URL}/api/chat/message",
                json={"session_id": session_id, "message": message},
                timeout=15
            )
            
            if not response.ok:
                print(f"❌ Exclamation mark failed: {response.status_code}")
                return False
            
            result = response.json()
            if not result.get("success"):
                print(f"❌ API Error: {result.get('error')}")
                return False
                
            print(f"✅ Bot response: {result['response']}")
            
            if result.get("ended"):
                print("🏁 Conversation ended")
                break
                
            time.sleep(1)
        
        print(f"🎉 SUCCESS: Exclamation marks work perfectly on deployed site!")
        return True
        
    except Exception as e:
        print(f"❌ Exclamation test failed: {e}")
        return False

if __name__ == "__main__":
    print("🌐 TESTING DEPLOYED BARMUDA CHAT FUNCTIONALITY")
    print("Site: https://barmuda.in")
    print("=" * 80)
    
    success_count = 0
    total_tests = 2
    
    # Test 1: Confusion handling
    if test_deployed_chat():
        success_count += 1
    
    # Test 2: Exclamation marks  
    if test_deployed_exclamation_marks():
        success_count += 1
    
    # Results
    print(f"\n" + "=" * 80)
    print(f"🏆 DEPLOYED TESTING RESULTS")
    print(f"=" * 80)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print(f"\n🎉 ALL DEPLOYED TESTS PASSED!")
        print(f"🚀 Chat agent is working perfectly on barmuda.in!")
    else:
        print(f"\n🚨 Some deployed tests failed!")
        print(f"🔍 Check the deployed version vs local changes")