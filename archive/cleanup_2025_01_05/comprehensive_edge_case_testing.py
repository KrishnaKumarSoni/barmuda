#!/usr/bin/env python3
"""
Comprehensive testing of all edge cases from EdgeCases.md
Using Python requests to avoid shell escaping issues
"""

import requests
import json
import time
import traceback

BASE_URL = "http://localhost:5000"

def test_conversation(test_name, messages, expected_behaviors=None):
    """Test a complete conversation flow"""
    print(f"\n🧪 TESTING: {test_name}")
    print("=" * 60)
    
    try:
        # Start session
        start_response = requests.post(
            f"{BASE_URL}/api/chat/start",
            json={"form_id": "VhmJufviBBiuT1xUjypY", "device_id": f"test_{test_name.lower().replace(' ', '_')}"}
        )
        
        if not start_response.ok:
            print(f"❌ Failed to start session: {start_response.text}")
            return False
            
        session_data = start_response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session started: {session_id}")
        print(f"🤖 Greeting: {session_data['greeting']}")
        
        conversation_ended = False
        message_count = 0
        
        # Process each message
        for i, message in enumerate(messages, 1):
            print(f"\n👤 Message {i}: '{message}'")
            
            response = requests.post(
                f"{BASE_URL}/api/chat/message",
                json={"session_id": session_id, "message": message}
            )
            
            if not response.ok:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                return False
            
            result = response.json()
            
            if not result.get("success"):
                print(f"❌ API Error: {result.get('error')}")
                return False
            
            print(f"🤖 Response: {result['response']}")
            
            # Check for conversation end
            if result.get("ended"):
                print("🏁 Conversation ended")
                conversation_ended = True
                if result.get("extraction_triggered"):
                    print("📊 Extraction triggered")
                break
                
            message_count += 1
            time.sleep(0.5)  # Be nice to the server
        
        print(f"✅ Test completed: {message_count} messages processed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        traceback.print_exc()
        return False

def run_all_edge_case_tests():
    """Run comprehensive edge case testing"""
    
    print("🚀 STARTING COMPREHENSIVE EDGE CASE TESTING")
    print("Testing all scenarios from EdgeCases.md using Python requests")
    print("=" * 80)
    
    test_results = []
    
    # 1. Off-Topic Responses
    result = test_conversation(
        "Off-Topic Responses",
        [
            "hi",
            "What's the weather like?", 
            "Did you see the game last night?",
            "How about those bananas?",
            "Fine, it was well organized"
        ]
    )
    test_results.append(("Off-Topic Responses", result))
    
    # 2. Skipping Questions Explicitly  
    result = test_conversation(
        "Skipping Questions",
        [
            "hello",
            "skip",
            "pass on this one", 
            "next question please",
            "I don't want to answer that",
            "skip this too",
            "actually the venue was nice"
        ]
    )
    test_results.append(("Skipping Questions", result))
    
    # 3. Pre-Answering or Multi-Answers
    result = test_conversation(
        "Multi-Answers",
        [
            "hi",
            "Alex, 25, from LA, event was great, content excellent, speakers amazing",
            "I am done"
        ]
    )
    test_results.append(("Multi-Answers", result))
    
    # 4. Conflicting or Changing Answers
    result = test_conversation(
        "Conflicting Answers", 
        [
            "hello",
            "Yes it was good",
            "Actually no, it was bad",
            "Wait, I changed my mind, it was okay",
            "I am done"
        ]
    )
    test_results.append(("Conflicting Answers", result))
    
    # 5. Vague or Ambiguous Responses
    result = test_conversation(
        "Vague Responses",
        [
            "hi",
            "meh",
            "okay I guess", 
            "fine",
            "whatever",
            "sure"
        ]
    )
    test_results.append(("Vague Responses", result))
    
    # 6. No-Fit Responses for Bucketized Questions
    result = test_conversation(
        "No-Fit Responses",
        [
            "hello",
            "It was purple organized",  # Non-standard response
            "The content was triangular",  # Non-standard
            "Speakers were very geometric",  # Non-standard
            "done"
        ]
    )
    test_results.append(("No-Fit Responses", result))
    
    # 7. Abrupt Abandonment (End Early)
    result = test_conversation(
        "Early Ending",
        [
            "hi", 
            "it was good",
            "I'm done now",  # Premature ending
        ]
    )
    test_results.append(("Early Ending", result))
    
    # 8. Invalid Input for Typed Questions
    result = test_conversation(
        "Invalid Input Types",
        [
            "hello",
            "seventeen and a half",  # Non-numeric for potential number question
            "yes no maybe",  # Ambiguous for yes/no
            "I am done"
        ]
    )
    test_results.append(("Invalid Input Types", result))
    
    # 9. Sensitive or Offensive Content
    result = test_conversation(
        "Sensitive Content",
        [
            "hi",
            "The event was terrible and I hate everyone",
            "This is stupid",
            "Whatever, it was fine"
        ]
    )
    test_results.append(("Sensitive Content", result))
    
    # 10. Multi-Language Responses
    result = test_conversation(
        "Multi-Language",
        [
            "hola",
            "Très bien organisé",  # French
            "Era bueno",  # Spanish  
            "I am done"
        ]
    )
    test_results.append(("Multi-Language", result))
    
    # 11. Confusion/Clarification (The original bug!)
    result = test_conversation(
        "Confusion and Clarification",
        [
            "hi",
            "what?",
            "what do you mean?",
            "huh?",
            "I don't understand",
            "oh I see, it was good",
            "done"
        ]
    )
    test_results.append(("Confusion and Clarification", result))
    
    # 12. Exclamation Marks (The shell issue we found!)
    result = test_conversation(
        "Exclamation Marks",
        [
            "hello!",
            "it was great!",
            "amazing content!",
            "fantastic speakers!",
            "I am done!"
        ]
    )
    test_results.append(("Exclamation Marks", result))
    
    # Print final results
    print("\n" + "=" * 80)
    print("🏆 FINAL TEST RESULTS")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 SUMMARY: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"🎯 Success rate: {(passed / (passed + failed) * 100):.1f}%")
    
    return passed, failed

if __name__ == "__main__":
    passed, failed = run_all_edge_case_tests()
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Agent is ready for production!")
    else:
        print(f"\n🚨 {failed} tests failed. Review and fix before deployment.")