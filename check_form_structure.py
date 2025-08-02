#!/usr/bin/env python3
"""
Check the form structure to understand question indexing
"""
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('bermuda-01-firebase-adminsdk-fbsvc-660474f630.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

def check_form_structure():
    """Check the form structure to understand question indices"""
    FORM_ID = "x4GZrJ1165MiMze4YC2Y"
    print(f"🔍 Checking form structure for: {FORM_ID}")
    
    # Get form
    form_doc = db.collection('forms').document(FORM_ID).get()
    
    if not form_doc.exists:
        print("❌ Form not found")
        return
    
    form_data = form_doc.to_dict()
    
    print(f"📊 Form Title: {form_data.get('title')}")
    print(f"📊 Total Questions: {len(form_data.get('questions', []))}")
    
    # Show all questions with their indices
    questions = form_data.get('questions', [])
    for i, question in enumerate(questions):
        print(f"   Q{i}: {question.get('text', 'No text')} ({question.get('type', 'unknown type')})")
    
    print(f"\n📊 Demographics: {form_data.get('demographics', {})}")

def check_response_indices():
    """Check what question indices exist in response data"""
    FORM_ID = "x4GZrJ1165MiMze4YC2Y"
    print(f"\n🔍 Checking response indices for: {FORM_ID}")
    
    # Get all responses
    responses = list(db.collection('responses').where('form_id', '==', FORM_ID).stream())
    
    all_indices = set()
    for response_doc in responses:
        response_data = response_doc.to_dict()
        if 'responses' in response_data:
            all_indices.update(response_data['responses'].keys())
    
    print(f"📊 Response indices found across all responses: {sorted(all_indices)}")
    
    # Show a sample response
    if responses:
        sample = responses[0].to_dict()
        if 'responses' in sample:
            print(f"📊 Sample response indices: {list(sample['responses'].keys())}")
            for key, value in sample['responses'].items():
                print(f"   Index {key}: '{value.get('value', 'N/A')}'")

if __name__ == "__main__":
    check_form_structure()
    check_response_indices()