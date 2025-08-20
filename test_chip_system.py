#!/usr/bin/env python3
"""
Test script to create a form with different question types and test the new chip system
"""

import os
import sys
import json
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up environment variables
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', '')

import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase if not already done
if not firebase_admin._apps:
    cred = credentials.Certificate('barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

def create_test_form():
    """Create a test form with different question types"""
    
    # Test form with different question types
    form_data = {
        "title": "Chip System Test Form",
        "created_at": datetime.now().isoformat(),
        "user_id": "test_user",
        "active": True,
        "questions": [
            {
                "text": "What's your favorite color?",
                "type": "multiple_choice",
                "options": ["Red", "Blue", "Green", "Yellow", "Purple"],
                "enabled": True
            },
            {
                "text": "Do you like pizza?",
                "type": "yes_no", 
                "enabled": True
            },
            {
                "text": "How would you rate this experience?",
                "type": "rating",
                "enabled": True
            },
            {
                "text": "Tell us about yourself",
                "type": "text",
                "enabled": True
            },
            {
                "text": "How many hours do you work per day?",
                "type": "number",
                "enabled": True
            }
        ],
        "demographics": {},
        "profile_data": {}
    }
    
    # Save to Firestore
    form_id = "chip_test_form_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_ref = db.collection('forms').document(form_id)
    doc_ref.set(form_data)
    
    print(f"✅ Created test form with ID: {form_id}")
    print(f"🔗 Test URL: http://localhost:5555/form/{form_id}")
    print(f"📊 Dashboard: http://localhost:5555/dashboard")
    
    return form_id

def test_old_vs_new_system():
    """Test both old and new prompt systems"""
    print("\n🧪 TESTING INSTRUCTIONS:")
    print("="*50)
    print("1. The simplified prompt is currently ENABLED")
    print("2. Test the form using the URL above")
    print("3. Look for:")
    print("   - Multiple choice questions should show clickable chips")
    print("   - Yes/No questions should show Yes/No chips") 
    print("   - Rating questions should show 1-5 chips")
    print("   - Text questions should NOT show chips")
    print("4. To test the OLD system:")
    print("   - Edit chat_engine.py")
    print("   - Set USE_SIMPLIFIED_PROMPT = False")
    print("   - Restart the server")
    print("   - Test again to compare")
    print("="*50)

if __name__ == "__main__":
    print("🚀 Creating test form for chip system...")
    form_id = create_test_form()
    test_old_vs_new_system()
    print("\n💡 Note: Make sure OPENAI_API_KEY is set in your environment!")