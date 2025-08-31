#!/usr/bin/env python3
"""Debug the exact Flask flow that's failing"""

import traceback
import sys
import json

# Simulate the exact Flask app flow
from chat_agent_v3 import get_chat_agent
from data_extraction import extract_chat_responses

def debug_flask_flow():
    """Debug the exact sequence that happens in Flask app"""
    session_id = "session_20250804_212438_2a53a702"
    message = "nope, all done!"
    
    print("🔍 DEBUGGING FLASK MESSAGE PROCESSING FLOW")
    print(f"Session ID: {session_id}")
    print(f"Message: '{message}'")
    print("-" * 50)
    
    try:
        # Step 1: Get agent (like Flask does)
        print("1️⃣ Getting chat agent...")
        agent = get_chat_agent()
        print("✅ Agent loaded")
        
        # Step 2: Process message (like Flask does)
        print("2️⃣ Processing message...")
        result = agent.process_message(session_id, message)
        print(f"✅ Message processed: success={result.get('success')}")
        
        if not result.get("success"):
            print(f"❌ Agent processing failed: {result.get('error')}")
            return
        
        # Step 3: Check if conversation ended (like Flask does)
        conversation_ended = result.get("metadata", {}).get("ended", False)
        print(f"3️⃣ Conversation ended: {conversation_ended}")
        
        # Step 4: Trigger extraction if ended (like Flask does)
        if conversation_ended:
            print("4️⃣ Triggering data extraction...")
            try:
                extraction_result = extract_chat_responses(session_id)
                print(f"✅ Extraction completed: {extraction_result}")
            except Exception as extraction_error:
                print(f"❌ EXTRACTION FAILED: {type(extraction_error).__name__}: {extraction_error}")
                print("📍 Extraction traceback:")
                traceback.print_exc()
                return
        
        print("🎉 ALL STEPS COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        print(f"❌ FLASK FLOW ERROR: {type(e).__name__}: {str(e)}")
        print(f"📍 Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    debug_flask_flow()