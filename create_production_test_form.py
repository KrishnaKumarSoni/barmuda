#!/usr/bin/env python3
"""
Create a comprehensive production test form for the polished chip system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json

def create_production_test_form():
    """Create a comprehensive test form for production chip testing"""
    
    # Initialize Firebase if not already done
    try:
        app = firebase_admin.get_app()
    except ValueError:
        # Initialize with service account
        cred_path = "service-account-key.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            print("❌ Service account key not found")
            return None
    
    db = firestore.client()
    
    # Form configuration
    form_id = "production_chip_test_2025"
    form_data = {
        "title": "Production Chip System Test",
        "description": "Comprehensive test form for the polished conversational chip system on barmuda.in",
        "active": True,
        "creator_id": "production_test",
        "created_at": datetime.utcnow(),
        "questions": [
            {
                "text": "What's your favorite streaming platform?",
                "type": "multiple_choice",
                "enabled": True,
                "options": ["Netflix", "Disney+", "Hulu", "HBO Max", "Amazon Prime"]
            },
            {
                "text": "Do you enjoy watching documentaries?", 
                "type": "yes_no",
                "enabled": True,
                "options": []
            },
            {
                "text": "How satisfied are you with your current streaming experience?",
                "type": "rating",
                "enabled": True,
                "options": []
            },
            {
                "text": "What genres do you watch most often?",
                "type": "multiple_choice", 
                "enabled": True,
                "options": ["Comedy", "Drama", "Action", "Sci-Fi", "Documentary", "Horror"]
            },
            {
                "text": "Would you recommend streaming services to friends?",
                "type": "yes_no",
                "enabled": True,
                "options": []
            },
            {
                "text": "How many hours per week do you spend streaming?",
                "type": "multiple_choice",
                "enabled": True,
                "options": ["0-5 hours", "6-10 hours", "11-20 hours", "20+ hours"]
            },
            {
                "text": "What's your ideal streaming session length?",
                "type": "multiple_choice",
                "enabled": True, 
                "options": ["30 minutes", "1 hour", "2-3 hours", "Binge all day"]
            },
            {
                "text": "Do you prefer movies or TV series?",
                "type": "multiple_choice",
                "enabled": True,
                "options": ["Movies", "TV Series", "Both equally", "Depends on mood"]
            },
            {
                "text": "Are you satisfied with streaming video quality?",
                "type": "yes_no", 
                "enabled": True,
                "options": []
            },
            {
                "text": "What's your biggest streaming frustration?",
                "type": "text",
                "enabled": True,
                "options": []
            }
        ]
    }
    
    try:
        # Create the form
        doc_ref = db.collection('forms').document(form_id)
        doc_ref.set(form_data)
        
        print("✅ Created production test form!")
        print(f"📋 Form ID: {form_id}")
        print(f"🔗 Test URL: https://barmuda.in/form/{form_id}")
        print(f"📊 Questions: {len(form_data['questions'])}")
        
        # Count questions by type
        type_counts = {}
        for q in form_data['questions']:
            q_type = q['type']
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
        
        print("📈 Question breakdown:")
        for q_type, count in type_counts.items():
            chip_support = "✅ Chips" if q_type in ['multiple_choice', 'yes_no', 'rating'] else "⭕ No chips"
            print(f"   • {q_type}: {count} questions ({chip_support})")
        
        return form_id
        
    except Exception as e:
        print(f"❌ Error creating form: {e}")
        return None

if __name__ == "__main__":
    form_id = create_production_test_form()
    if form_id:
        print(f"\n🚀 Ready for production testing!")
        print(f"🌐 Visit: https://barmuda.in/form/{form_id}")