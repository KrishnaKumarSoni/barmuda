#!/usr/bin/env python3
"""
Setup script to configure Groq API for Barmuda
Run this once to set up your environment variables
"""

import os
from dotenv import load_dotenv, set_key

def setup_groq():
    """Set up Groq API configuration"""
    load_dotenv()
    
    # Get Groq API key from user input or environment
    groq_api_key = input("Enter your Groq API key: ").strip()
    if not groq_api_key:
        print("❌ No API key provided. Exiting...")
        return
    
    print("🚀 Setting up Groq API for ultra-fast inference...")
    
    # Set environment variables in .env file
    env_file = ".env"
    
    # Add Groq configuration
    set_key(env_file, "GROQ_API_KEY", groq_api_key)
    set_key(env_file, "USE_GROQ", "true")
    
    print("✅ Groq API configured successfully!")
    print(f"✅ API Key: {groq_api_key[:20]}...")
    print("✅ USE_GROQ: true")
    print("\n🎯 Groq Features:")
    print("   • Model: OpenAI GPT-OSS 20B (20 billion parameters)")
    print("   • Context: 131,072 tokens (128k context window)")
    print("   • Speed: ~1000 tokens/sec (ultra-fast)")
    print("   • Architecture: Same as your existing setup")
    
    print("\n🔄 Restart your Flask server to use Groq!")
    print("   Expected response time: 1-2 seconds (vs 6-9 seconds)")

def setup_openai_fallback():
    """Set up OpenAI as fallback (disable Groq)"""
    load_dotenv()
    
    print("🔗 Configuring OpenAI fallback...")
    
    env_file = ".env"
    set_key(env_file, "USE_GROQ", "false")
    
    print("✅ OpenAI fallback configured!")
    print("✅ USE_GROQ: false")
    print("\n🔄 Restart your Flask server to use OpenAI!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "openai":
        setup_openai_fallback()
    else:
        setup_groq()