#!/usr/bin/env python3
"""Test a single chat conversation"""

from chat_agent_v3 import get_chat_agent
import time

# Create agent and session
agent = get_chat_agent()
session_id = agent.create_session('VhmJufviBBiuT1xUjypY', 'single_test_device')
print(f"Session: {session_id}\n")

# Simulate conversation
messages = [
    "hi",
    "what do you mean?",
    "oh I see, it was pretty good actually",
    "what?", 
    "the content was excellent",
    "skip",
    "the venue was nice",
    "banana",
    "alright fine, 4 out of 5"
]

# Initial greeting
result = agent.process_message(session_id, "Hello!")
print(f"Bot: {result['response']}\n")

# Process messages
for msg in messages:
    print(f"User: {msg}")
    result = agent.process_message(session_id, msg)
    print(f"Bot: {result['response']}")
    
    # Check metadata
    metadata = result.get('metadata', {})
    if metadata.get('redirect_count', 0) > 0:
        print(f"[Redirect count: {metadata['redirect_count']}]")
    if metadata.get('skip_count', 0) > 0:
        print(f"[Skips: {metadata['skip_count']}]")
    if metadata.get('ended', False):
        print("[CONVERSATION ENDED]")
        break
    
    print()