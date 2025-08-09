#!/usr/bin/env python3
"""
Interactive chat test - actually chat with the bot locally
"""

import os
from dotenv import load_dotenv
load_dotenv()

from chat_engine import get_chat_agent

def interactive_chat_test():
    """Test the chat with real human interaction"""
    
    print("=== INTERACTIVE CHAT TEST ===")
    form_id = '6Mywt1rZQi2oNfFt27Na'
    
    try:
        # Create agent and session
        agent = get_chat_agent()
        session_id = agent.create_session(form_id, device_id='interactive_test')
        print(f"✓ Session started: {session_id}")
        print("✓ Chat with the bot! Type 'quit' to exit\n")
        
        while True:
            # Get user input
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Chat ended!")
                break
                
            if not user_input:
                continue
                
            # Process message
            response = agent.process_message(session_id, user_input)
            
            if response['success']:
                bot_response = response['response']
                print(f"Bot: {bot_response}\n")
            else:
                print(f"❌ Error: {response.get('error', 'Unknown error')}")
                print(f"Fallback: {response.get('response', 'None')}\n")
                
    except KeyboardInterrupt:
        print("\n👋 Chat interrupted!")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    interactive_chat_test()