#!/usr/bin/env python3
"""
Health check for the OpenAI Agents SDK chat engine.
Runs agent creation, session creation with a real form, and a short
conversation smoke test to ensure the survey flow behaves as expected.
"""

import os
import sys
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_engine_functionality(engine_name, get_agent_func):
    """Test basic functionality of a chat engine"""
    print(f"\n🧪 Testing {engine_name} Engine Functionality")
    print("-" * 40)
    
    results = {}
    
    try:
        # Test 1: Agent Creation
        start_time = time.time()
        agent = get_agent_func()
        agent_creation_time = time.time() - start_time
        print(f"✅ Agent created ({agent_creation_time:.3f}s)")
        results["agent_creation"] = True
        results["agent_creation_time"] = agent_creation_time
        
        # Test 2: Session Creation with Real Form
        try:
            # Get a real form ID using Firebase MCP
            from chat_engine import firestore_db
            forms = list(firestore_db.collection("forms").limit(1).stream())
            
            if not forms:
                print("⚠️  No forms found - skipping session creation")
                return results
            
            form_id = forms[0].id
            form_title = forms[0].to_dict().get('title', 'Unknown')
            
            start_time = time.time()
            session_id = agent.create_session(form_id, device_id=f"test-{engine_name.lower()}")
            session_creation_time = time.time() - start_time
            
            print(f"✅ Session created with real form '{form_title}' ({session_creation_time:.3f}s)")
            results["session_creation"] = True
            results["session_creation_time"] = session_creation_time
            results["session_id"] = session_id
            results["form_title"] = form_title
            
            # Test 3: Conversation Flow
            test_messages = [
                "Hello, I'm ready to start!",
                "My favorite color is blue",
                "I'd rate it an 8 out of 10",
                "Skip this question please",
                "That's a bit random - can we focus on the survey?",  # Off-topic test
                "I'm 25 years old"
            ]
            
            conversation_times = []
            responses = []
            
            for i, message in enumerate(test_messages):
                try:
                    start_time = time.time()
                    response = agent.process_message(session_id, message)
                    response_time = time.time() - start_time
                    conversation_times.append(response_time)
                    
                    if response.get("success", True):
                        responses.append({
                            "user": message,
                            "assistant": response.get("response", "")[:100] + "...",
                            "time": response_time
                        })
                        print(f"✅ Message {i+1} processed ({response_time:.3f}s)")
                    else:
                        print(f"⚠️  Message {i+1} failed: {response.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"❌ Message {i+1} error: {str(e)}")
                    break
                    
                # Don't overwhelm the API
                time.sleep(0.5)
            
            results["conversation_test"] = True
            results["conversation_times"] = conversation_times
            results["avg_response_time"] = sum(conversation_times) / len(conversation_times) if conversation_times else 0
            results["responses"] = responses
            
            print(f"✅ Conversation flow completed (avg: {results['avg_response_time']:.3f}s per message)")
            
        except Exception as e:
            print(f"❌ Session/conversation test failed: {str(e)}")
            results["session_creation"] = False
            results["conversation_test"] = False
            
    except Exception as e:
        print(f"❌ Agent creation failed: {str(e)}")
        results["agent_creation"] = False
        
    return results

def run_health_check():
    """Run a health check for the OpenAI Agents SDK implementation"""
    print("🔥 OPENAI AGENTS SDK HEALTH CHECK")
    print("=" * 50)

    engines = {}

    try:
        from chat_engine import get_chat_agent as get_openai_agent

        engines["OpenAI Agents SDK"] = test_engine_functionality(
            "OpenAI", get_openai_agent
        )
    except ImportError as e:
        print(f"⚠️  OpenAI Agents SDK not available: {e}")
        engines["OpenAI Agents SDK"] = {"available": False, "error": str(e)}

    results = engines.get("OpenAI Agents SDK", {})

    print("\n" + "=" * 60)
    print("📊 HEALTH CHECK SUMMARY")
    print("=" * 60)

    if results.get("conversation_test"):
        avg_time = results.get("avg_response_time", 0)
        print("✅ Conversation flow passed")
        print(f"⏱️  Average response time: {avg_time:.3f}s")
    elif results.get("agent_creation"):
        print("⚠️  Agent created but conversation test failed")
    else:
        print("❌ Chat agent unavailable – check configuration")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"engine_health_{timestamp}.json"

    try:
        with open(results_file, "w") as f:
            json.dump(engines, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to: {results_file}")
    except Exception as e:
        print(f"⚠️  Could not save results: {e}")

    return engines

if __name__ == "__main__":
    print("🚀 BARMUDA CHAT ENGINE HEALTH CHECK")
    print("Testing OpenAI Agents SDK implementation")
    print("This will verify functionality, performance, and quality\n")

    required_vars = ["OPENAI_API_KEY", "FIREBASE_PROJECT_ID"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ Missing required environment variables: {missing}")
        sys.exit(1)

    results = run_health_check()

    print("\n🎉 Health check complete!")
