#!/usr/bin/env python3
"""Debug the specific error with 'nope, all done!' message"""

import traceback
from chat_agent_v3 import get_chat_agent

def debug_message_processing():
    """Debug the exact error that occurs"""
    session_id = "session_20250804_212240_adcd9718"
    message = "nope, all done!"
    
    try:
        print(f"🔍 Testing message: '{message}'")
        print(f"🔍 Session ID: {session_id}")
        
        agent = get_chat_agent()
        print("✅ Agent loaded successfully")
        
        print("🔍 Processing message...")
        result = agent.process_message(session_id, message)
        
        print("✅ Message processed successfully!")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"❌ ERROR CAUGHT: {type(e).__name__}: {str(e)}")
        print(f"📍 Full traceback:")
        traceback.print_exc()
        
        # Check if it's a specific type of error
        if "extract" in str(e).lower():
            print("🎯 This appears to be an extraction-related error")
        elif "firebase" in str(e).lower():
            print("🎯 This appears to be a Firebase-related error")
        elif "openai" in str(e).lower():
            print("🎯 This appears to be an OpenAI API error")
        else:
            print("🎯 This is a different type of error")

if __name__ == "__main__":
    debug_message_processing()