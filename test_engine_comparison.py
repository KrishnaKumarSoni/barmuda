#!/usr/bin/env python3
"""
Comprehensive comparison test between OpenAI Agents SDK and Groq engines
Tests functionality, performance, and quality side by side
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
            from groq_chat_engine import firestore_db
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

def run_comparison_test():
    """Run comprehensive comparison between engines"""
    print("🔥 COMPREHENSIVE ENGINE COMPARISON")
    print("=" * 50)
    
    # Test both engines
    engines = {}
    
    # Test OpenAI Agents SDK
    try:
        from chat_engine import get_chat_agent as get_openai_agent
        engines["OpenAI Agents SDK"] = test_engine_functionality("OpenAI", get_openai_agent)
    except ImportError as e:
        print(f"⚠️  OpenAI Agents SDK not available: {e}")
        engines["OpenAI Agents SDK"] = {"available": False, "error": str(e)}
    
    # Test Groq
    try:
        from groq_chat_engine import get_chat_agent as get_groq_agent
        engines["Groq"] = test_engine_functionality("Groq", get_groq_agent)
    except ImportError as e:
        print(f"⚠️  Groq engine not available: {e}")
        engines["Groq"] = {"available": False, "error": str(e)}
    
    # Generate comparison report
    print("\n" + "=" * 60)
    print("📊 DETAILED COMPARISON REPORT")
    print("=" * 60)
    
    # Performance comparison
    if "OpenAI Agents SDK" in engines and "Groq" in engines:
        openai_results = engines["OpenAI Agents SDK"]
        groq_results = engines["Groq"]
        
        # Response time comparison
        if openai_results.get("avg_response_time") and groq_results.get("avg_response_time"):
            openai_avg = openai_results["avg_response_time"]
            groq_avg = groq_results["avg_response_time"]
            speedup = openai_avg / groq_avg if groq_avg > 0 else 0
            
            print(f"\n⚡ PERFORMANCE COMPARISON:")
            print(f"   OpenAI Average:  {openai_avg:.3f}s per message")
            print(f"   Groq Average:    {groq_avg:.3f}s per message")
            print(f"   Speedup:         {speedup:.1f}x {'🚀' if speedup > 1 else '🐌'}")
        
        # Functionality comparison
        print(f"\n🔧 FUNCTIONALITY COMPARISON:")
        features = ["agent_creation", "session_creation", "conversation_test"]
        
        for feature in features:
            openai_ok = openai_results.get(feature, False)
            groq_ok = groq_results.get(feature, False)
            
            openai_status = "✅" if openai_ok else "❌"
            groq_status = "✅" if groq_ok else "❌"
            
            print(f"   {feature.replace('_', ' ').title():20} OpenAI: {openai_status}  Groq: {groq_status}")
        
        # Sample conversation quality
        if openai_results.get("responses") and groq_results.get("responses"):
            print(f"\n💬 SAMPLE CONVERSATION QUALITY:")
            print(f"   OpenAI responses: {len(openai_results['responses'])} messages")
            print(f"   Groq responses:   {len(groq_results['responses'])} messages")
            
            # Show first response comparison
            if openai_results["responses"] and groq_results["responses"]:
                print(f"\n   First Response Comparison:")
                print(f"   OpenAI: {openai_results['responses'][0]['assistant']}")
                print(f"   Groq:   {groq_results['responses'][0]['assistant']}")
    
    # Overall recommendation
    print(f"\n🎯 RECOMMENDATION:")
    
    if engines.get("Groq", {}).get("conversation_test", False):
        if engines.get("OpenAI Agents SDK", {}).get("conversation_test", False):
            groq_avg = engines["Groq"].get("avg_response_time", 999)
            openai_avg = engines["OpenAI Agents SDK"].get("avg_response_time", 999)
            
            if groq_avg < openai_avg * 0.8:  # At least 20% faster
                print(f"   ✅ SWITCH TO GROQ - Significantly faster ({groq_avg:.3f}s vs {openai_avg:.3f}s)")
                print(f"   🚀 Set USE_GROQ=true in .env to enable")
            else:
                print(f"   ⚖️  PERFORMANCE SIMILAR - Either engine works well")
                print(f"   💡 Try Groq for potential speed benefits")
        else:
            print(f"   ✅ USE GROQ - OpenAI engine has issues")
    elif engines.get("OpenAI Agents SDK", {}).get("conversation_test", False):
        print(f"   ✅ STICK WITH OPENAI - Groq engine has issues")
    else:
        print(f"   ❌ BOTH ENGINES HAVE ISSUES - Check configuration")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"engine_comparison_{timestamp}.json"
    
    try:
        with open(results_file, 'w') as f:
            json.dump(engines, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to: {results_file}")
    except Exception as e:
        print(f"⚠️  Could not save results: {e}")
    
    return engines

if __name__ == "__main__":
    print("🚀 BARMUDA CHAT ENGINE COMPARISON")
    print("Testing OpenAI Agents SDK vs Groq implementation")
    print("This will test functionality, performance, and quality\n")
    
    # Check environment
    required_vars = ["OPENAI_API_KEY", "GROQ_API_KEY", "FIREBASE_PROJECT_ID"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing required environment variables: {missing}")
        sys.exit(1)
    
    # Run comparison
    results = run_comparison_test()
    
    print(f"\n🎉 Comparison complete!")
    print(f"   Current setting: USE_GROQ={os.getenv('USE_GROQ', 'false')}")
    print(f"   Change in .env file to switch engines")