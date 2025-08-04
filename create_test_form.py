#!/usr/bin/env python3
"""Create a test form for chat testing"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase if not already done
if not firebase_admin._apps:
    cred = credentials.Certificate("barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Create test form
test_form = {
    "form_id": "VhmJufviBBiuT1xUjypY",
    "title": "Event Feedback Survey", 
    "active": True,  # Make it active for testing
    "creator_id": "test_user",
    "created_at": datetime.now(),
    "questions": [
        {
            "text": "How would you rate the overall organization of the event?",
            "type": "text",
            "enabled": True
        },
        {
            "text": "What did you think about the content quality?",
            "type": "text", 
            "enabled": True
        },
        {
            "text": "How were the speakers?",
            "type": "text",
            "enabled": True
        },
        {
            "text": "How was the networking experience?",
            "type": "text",
            "enabled": True
        },
        {
            "text": "Would you recommend this event to others?",
            "type": "yes_no",
            "enabled": True
        }
    ]
}

# Save to Firestore
db.collection("forms").document("VhmJufviBBiuT1xUjypY").set(test_form)
print("✅ Test form created successfully with ID: VhmJufviBBiuT1xUjypY")
print("✅ Form is active and ready for testing")