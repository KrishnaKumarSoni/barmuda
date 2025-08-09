#!/usr/bin/env python3
"""
Test the chat engine with the problematic form to identify RCA
"""

import os
from dotenv import load_dotenv
load_dotenv()

# Test the chat engine
from chat_engine import get_chat_agent, FormChatAgent

def test_conversation():
    """Test the conversation that was problematic"""
    
    print("=== TESTING CHAT ENGINE RCA ===")
    
    # Get form ID from URL
    form_id = '6Mywt1rZQi2oNfFt27Na'
    
    try:
        # Create agent
        agent = get_chat_agent()
        print("✓ Agent created successfully")
        
        # Create session
        session_id = agent.create_session(form_id, device_id='test_device_123')
        print(f"✓ Session created: {session_id}")
        
        # Test the problematic conversation
        messages = [
            "death",  # User's concerning response
            "death",  # User repeats it
            "are you alive?",  # User asks about bot's response
            "it's surprising to see you didn't follow up about death."  # User calls out poor behavior
        ]
        
        for i, msg in enumerate(messages, 1):
            print(f"\n--- Message {i}: User says '{msg}' ---")
            
            response = agent.process_message(session_id, msg)
            
            if response['success']:
                bot_response = response['response']
                print(f"Bot: {bot_response}")
                
                # Check if bot is being contextual
                if 'death' in msg.lower() and 'death' not in bot_response.lower():
                    print("🚨 WARNING: Bot ignored concerning content!")
                    
                if 'are you alive' in msg.lower() and 'alive' not in bot_response.lower():
                    print("🚨 WARNING: Bot ignored direct question!")
                    
            else:
                print(f"❌ Error: {response.get('error', 'Unknown error')}")
                print(f"Fallback response: {response.get('response', 'None')}")
                break
    
    except Exception as e:
        import traceback
        print(f"❌ Test failed: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_conversation()