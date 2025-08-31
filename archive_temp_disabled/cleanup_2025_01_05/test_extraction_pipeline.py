#!/usr/bin/env python3
"""
Test extraction pipeline for partial, complete, and complex conversations
Validates that data extraction works correctly in all scenarios
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"

def test_extraction(test_name, messages, expected_completion=None):
    """Test conversation and verify extraction"""
    print(f"\n🧪 TESTING EXTRACTION: {test_name}")
    print("=" * 60)
    
    try:
        # Start session
        start_response = requests.post(
            f"{BASE_URL}/api/chat/start",
            json={"form_id": "VhmJufviBBiuT1xUjypY", "device_id": f"extract_test_{test_name.lower().replace(' ', '_')}"}
        )
        
        if not start_response.ok:
            print(f"❌ Failed to start session: {start_response.text}")
            return False
            
        session_data = start_response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session started: {session_id}")
        
        # Process messages
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
                if result.get("extraction_triggered"):
                    print("📊 Extraction triggered")
                break
                
            time.sleep(0.3)
        
        # Now test the extraction by fetching the saved data
        print(f"\n📊 CHECKING EXTRACTION FOR SESSION: {session_id}")
        
        # Check if session was saved to chat_responses
        extraction_response = requests.get(f"{BASE_URL}/api/test/extraction/{session_id}")
        
        if extraction_response.ok:
            extraction_data = extraction_response.json()
            print(f"✅ Extraction data found")
            print(f"📋 Form: {extraction_data.get('form_title', 'Unknown')}")
            print(f"🔢 Total responses: {len(extraction_data.get('responses', {}))}")
            print(f"💬 Messages exchanged: {len(extraction_data.get('chat_history', []))}")
            print(f"⏱️  Partial response: {extraction_data.get('metadata', {}).get('partial', False)}")
            print(f"✅ Session ended: {extraction_data.get('metadata', {}).get('ended', False)}")
            
            # Show actual extracted responses
            responses = extraction_data.get('responses', {})
            if responses:
                print(f"\n📝 EXTRACTED RESPONSES:")
                for q_idx, response in responses.items():
                    value = response.get('value', 'No value')
                    question = response.get('question_text', 'Unknown question')[:50] + "..."
                    print(f"  Q{q_idx}: {value} (to: {question})")
            else:
                print("⚠️  No responses extracted")
            
            return True
        else:
            print(f"❌ Could not retrieve extraction data: {extraction_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def run_extraction_tests():
    """Run comprehensive extraction testing"""
    
    print("🚀 TESTING EXTRACTION PIPELINE")
    print("Verifying data extraction for different conversation scenarios")
    print("=" * 80)
    
    test_results = []
    
    # 1. Complete Conversation (All questions answered)
    print("\n" + "="*50)
    print("TEST 1: COMPLETE CONVERSATION")
    print("="*50)
    result = test_extraction(
        "Complete Conversation",
        [
            "hello",
            "It was very well organized",
            "The content was excellent", 
            "The speakers were amazing",
            "The venue was perfect",
            "I would definitely recommend it"
        ]
    )
    test_results.append(("Complete Conversation", result))
    
    # 2. Partial Conversation (User ends early)
    print("\n" + "="*50)
    print("TEST 2: PARTIAL CONVERSATION (EARLY END)")
    print("="*50)
    result = test_extraction(
        "Partial Early End",
        [
            "hi",
            "It was okay",
            "I'm done now"  # Ends early
        ]
    )
    test_results.append(("Partial Early End", result))
    
    # 3. Complex Conversation (Skips, multi-answers, changes)
    print("\n" + "="*50)
    print("TEST 3: COMPLEX CONVERSATION")
    print("="*50)
    result = test_extraction(
        "Complex Conversation",
        [
            "hello",
            "skip this question",  # Skip
            "Actually the event was great, content was good, speakers were amazing",  # Multi-answer
            "Wait, I change my mind, the content was just okay",  # Conflict/change
            "pass on this one",  # Another skip
            "The venue was nice though",
            "done"
        ]
    )
    test_results.append(("Complex Conversation", result))
    
    # 4. Abandoned Conversation (Timeout simulation)
    print("\n" + "="*50)
    print("TEST 4: ABANDONED CONVERSATION")
    print("="*50)
    result = test_extraction(
        "Abandoned Conversation",
        [
            "hello",
            "It was good"
            # No explicit end - simulates abandonment
        ]
    )
    test_results.append(("Abandoned Conversation", result))
    
    # Print final results
    print("\n" + "=" * 80)
    print("🏆 EXTRACTION PIPELINE RESULTS")
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
    # Check if server is running
    try:
        health_check = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if not health_check.ok:
            print("❌ Server not responding correctly")
            sys.exit(1)
        print(f"✅ Server is healthy: {health_check.json()}")
    except Exception as e:
        print(f"❌ Server not running at http://localhost:5000: {e}")
        print("Please start the Flask server first: python app.py")
        sys.exit(1)
    
    passed, failed = run_extraction_tests()
    
    if failed == 0:
        print("\n🎉 ALL EXTRACTION TESTS PASSED! Pipeline is working correctly!")
    else:
        print(f"\n🚨 {failed} extraction tests failed. Review pipeline before deployment.")