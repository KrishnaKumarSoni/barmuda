#!/usr/bin/env python3
"""
Focused edge case testing - key scenarios only
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def quick_test(test_name, messages):
    """Quick test without extensive logging"""
    try:
        # Start session
        start_response = requests.post(
            f"{BASE_URL}/api/chat/start",
            json={"form_id": "VhmJufviBBiuT1xUjypY", "device_id": f"quick_{test_name.lower().replace(' ', '_')}"}
        )
        
        if not start_response.ok:
            return False, f"Start failed: {start_response.text}"
            
        session_id = start_response.json()["session_id"]
        
        # Process messages quickly
        for message in messages:
            response = requests.post(
                f"{BASE_URL}/api/chat/message",
                json={"session_id": session_id, "message": message}
            )
            
            if not response.ok:
                return False, f"Message failed: {response.text}"
            
            result = response.json()
            if not result.get("success"):
                return False, f"API Error: {result.get('error')}"
            
            if result.get("ended"):
                return True, "Conversation ended successfully"
                
            time.sleep(0.3)  # Quick delay
        
        return True, "Test completed"
        
    except Exception as e:
        return False, f"Exception: {e}"

def run_focused_tests():
    """Run focused edge case tests"""
    
    print("🚀 FOCUSED EDGE CASE TESTING")
    print("=" * 50)
    
    tests = [
        ("Confusion Handling", ["hi", "what?", "what do you mean?", "oh, it was good", "done"]),
        ("Exclamation Marks", ["hello!", "great event!", "amazing!", "I am done!"]),
        ("Skip Handling", ["hi", "skip", "pass", "next", "done"]),
        ("Off-Topic", ["hello", "bananas", "weather", "fine, it was good", "done"]),
        ("Multi-Answers", ["hi", "Good event, great content, amazing speakers", "done"]),
        ("Vague Responses", ["hi", "meh", "okay", "whatever", "done"]),
        ("Early Ending", ["hello", "I'm done now"]),
    ]
    
    results = []
    
    for test_name, messages in tests:
        print(f"\n🧪 Testing: {test_name}")
        success, message = quick_test(test_name, messages)
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        results.append((test_name, success))
        
        if not success:
            print(f"   Details: {message}")
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n📊 RESULTS: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    return passed, total

if __name__ == "__main__":
    passed, total = run_focused_tests()
    
    if passed == total:
        print(f"\n🎉 ALL {total} FOCUSED TESTS PASSED!")
    else:
        print(f"\n🚨 {total - passed} tests failed out of {total}")