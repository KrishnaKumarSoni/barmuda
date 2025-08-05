#!/usr/bin/env python3
"""Debug the extraction phase specifically"""

import traceback
from data_extraction import extract_chat_responses

def debug_extraction():
    """Debug the extraction that's called when conversation ends"""
    session_id = "session_20250804_212240_adcd9718"
    
    try:
        print(f"🔍 Testing extraction for session: {session_id}")
        
        print("🔍 Calling extract_chat_responses...")
        result = extract_chat_responses(session_id)
        
        print("✅ Extraction completed successfully!")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"❌ EXTRACTION ERROR: {type(e).__name__}: {str(e)}")
        print(f"📍 Full traceback:")
        traceback.print_exc()
        
        # Analyze the error
        error_str = str(e).lower()
        if "session not found" in error_str:
            print("🎯 Session doesn't exist in Firestore")
        elif "openai" in error_str:
            print("🎯 OpenAI API error during extraction")
        elif "firebase" in error_str:
            print("🎯 Firebase error during extraction")
        else:
            print("🎯 Unknown extraction error")

if __name__ == "__main__":
    debug_extraction()