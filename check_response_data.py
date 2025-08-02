#!/usr/bin/env python3
"""
Check the structure of extracted response data
"""
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('bermuda-01-firebase-adminsdk-fbsvc-660474f630.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

def check_response_structure():
    """Check one response to verify data structure"""
    FORM_ID = "x4GZrJ1165MiMze4YC2Y"
    print(f"🔍 Checking response structure for form: {FORM_ID}")
    
    # Get one response
    responses = list(db.collection('responses').where('form_id', '==', FORM_ID).limit(1).stream())
    
    if not responses:
        print("❌ No responses found")
        return
    
    response_doc = responses[0]
    response_data = response_doc.to_dict()
    
    print(f"📊 Response ID: {response_doc.id}")
    print(f"📊 Keys: {list(response_data.keys())}")
    
    # Check if 'responses' field contains extracted data
    if 'responses' in response_data:
        extracted_responses = response_data['responses']
        print(f"📊 Extracted responses keys: {list(extracted_responses.keys())}")
        
        # Show first few responses
        for key, value in list(extracted_responses.items())[:3]:
            print(f"   Q{key}: {value}")
    else:
        print("❌ No 'responses' field found")
    
    # Check other important fields
    metadata = response_data.get('metadata', {})
    print(f"📊 Metadata: {metadata}")
    
    partial = response_data.get('partial', False)
    print(f"📊 Partial: {partial}")

if __name__ == "__main__":
    check_response_structure()