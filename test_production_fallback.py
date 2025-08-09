#!/usr/bin/env python3
"""
Test what happens when chat_engine import fails in production
"""

import sys
import traceback

def test_import_failure():
    """Simulate what happens in production when imports fail"""
    
    print("=== TESTING PRODUCTION IMPORT BEHAVIOR ===")
    
    # Simulate the production code path
    try:
        print("\n1. Attempting to import chat_engine...")
        from chat_engine import get_chat_agent
        print("✓ Import successful")
        
        print("\n2. Attempting to create agent...")
        agent = get_chat_agent()
        print("✓ Agent created successfully")
        
    except ImportError as e:
        print(f"❌ ImportError: {e}")
        print("\nThis is what happens in production - the import fails!")
        print("Production would need to either:")
        print("  1. Have a fallback chat system")
        print("  2. Return an error")
        print("  3. Use a different chat implementation")
        
    except Exception as e:
        print(f"❌ Other error: {e}")
        traceback.print_exc()

def check_openai_agents_package():
    """Check if openai-agents package is properly installed"""
    
    print("\n=== CHECKING OPENAI-AGENTS PACKAGE ===")
    
    try:
        import agents
        print("✓ 'agents' module found")
        print(f"  Location: {agents.__file__ if hasattr(agents, '__file__') else 'built-in'}")
        
        from agents import Agent, Runner, function_tool
        print("✓ Can import Agent, Runner, function_tool from agents")
        
    except ImportError as e:
        print(f"❌ Cannot import agents: {e}")
        print("\nThis means openai-agents package is NOT properly installed!")
        print("In production, this would cause chat_engine.py to fail at line 15:")
        print("  from agents import Agent, Runner, function_tool")

if __name__ == "__main__":
    check_openai_agents_package()
    print("\n" + "="*50)
    test_import_failure()