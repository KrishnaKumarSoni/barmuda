#!/usr/bin/env python3
"""
Test chat agent v3 with multiple realistic conversations
Simulating API-like interactions
"""

import json
import time
from chat_agent_v3 import get_chat_agent

def print_conversation_header(conv_num, scenario):
    print(f"\n{'='*60}")
    print(f"CONVERSATION {conv_num}: {scenario}")
    print(f"{'='*60}\n")

def simulate_api_chat(messages, form_id='VhmJufviBBiuT1xUjypY', device_id=None):
    """Simulate a chat conversation through API-like calls"""
    agent = get_chat_agent()
    
    # Simulate /api/chat/start
    session_id = agent.create_session(form_id, device_id or f'test_device_{int(time.time())}')
    print(f"📍 Session started: {session_id}")
    
    # Initial greeting
    result = agent.process_message(session_id, "Hello, I'm ready to start!")
    print(f"🤖 Bot: {result['response']}")
    
    # Process each user message
    for i, msg in enumerate(messages, 1):
        print(f"\n👤 User: {msg}")
        
        # Simulate /api/chat/message
        result = agent.process_message(session_id, msg)
        
        print(f"🤖 Bot: {result['response']}")
        
        # Check if conversation ended
        if result.get('metadata', {}).get('ended', False):
            print("\n✅ Conversation ended")
            break
            
        # Small delay to simulate real conversation
        time.sleep(0.5)
    
    return session_id

# CONVERSATION 1: Confused User
print_conversation_header(1, "Confused User - Lots of Clarifications")
messages1 = [
    "hey",
    "what?", 
    "i don't understand",
    "what are you asking?",
    "oh you mean how the event went?",
    "it was good",
    "huh?",
    "the presentations were interesting",
    "what do you mean?",
    "oh the speakers? they were knowledgeable"
]
simulate_api_chat(messages1)

# CONVERSATION 2: Skip Happy User
print_conversation_header(2, "User Who Skips Multiple Questions")
messages2 = [
    "hi there",
    "skip",
    "pass on this one",
    "next question please",
    "I don't want to answer that",
    "actually it was well organized",
    "skip this too",
    "the venue was nice"
]
simulate_api_chat(messages2)

# CONVERSATION 3: Off-Topic User
print_conversation_header(3, "User Goes Off-Topic Multiple Times")
messages3 = [
    "hello",
    "what's the weather like?",
    "did you see the game last night?",
    "fine, it was organized well",
    "banana",
    "ok ok, the content was good",
    "buttermilk",
    "alright I'm done with this"
]
simulate_api_chat(messages3)

# CONVERSATION 4: Page Refresh Simulation
print_conversation_header(4, "User Refreshes Page Mid-Conversation")
# First part of conversation
messages4_part1 = [
    "hi",
    "the event was fantastic",
    "content was very relevant", 
    "speakers did great"
]
session_id = simulate_api_chat(messages4_part1, device_id='refresh_test_device')

print("\n\n⚡ SIMULATING PAGE REFRESH - Same device reconnects...")
time.sleep(3)  # Simulate 3 second gap

# Reconnect with same device_id - should find existing session
agent = get_chat_agent()
# In real app, this would be handled by /api/chat/start finding existing session
# For now, we'll continue with same session_id
print(f"📍 Resuming session: {session_id}")

messages4_part2 = [
    "hello again",
    "where were we?",
    "oh right, the networking was good",
    "yes, I'd recommend it"
]
for msg in messages4_part2:
    print(f"\n👤 User: {msg}")
    result = agent.process_message(session_id, msg)
    print(f"🤖 Bot: {result['response']}")
    time.sleep(0.5)

# CONVERSATION 5: Natural Complete Flow
print_conversation_header(5, "Natural Complete Conversation")
messages5 = [
    "hey there!",
    "yeah it was pretty well organized, I'd say 4 out of 5",
    "content was excellent - very relevant to my work",
    "the keynote speaker was amazing, others were good too",
    "networking was okay, could have been better",
    "4",  # Rating question
    "more time for Q&A sessions would be nice",
    "yes definitely",
    "thanks, bye!"
]
simulate_api_chat(messages5)

print("\n\n✨ All conversations completed!")