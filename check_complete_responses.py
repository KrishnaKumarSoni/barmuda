#!/usr/bin/env python3
"""
Check which questions have actual response data
"""
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('bermuda-01-firebase-adminsdk-fbsvc-660474f630.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

def analyze_response_coverage():
    """Analyze which questions have response data"""
    FORM_ID = "x4GZrJ1165MiMze4YC2Y"
    print(f"🔍 Analyzing response coverage for: {FORM_ID}")
    
    # Get all responses
    responses = list(db.collection('responses').where('form_id', '==', FORM_ID).stream())
    print(f"📊 Total responses: {len(responses)}")
    
    # Track question coverage
    question_counts = {}
    
    for i, response_doc in enumerate(responses):
        response_data = response_doc.to_dict()
        response_id = response_doc.id
        partial = response_data.get('partial', False)
        
        print(f"\n📝 Response {i+1} (ID: {response_id[:8]}...) - Partial: {partial}")
        
        if 'responses' in response_data:
            response_answers = response_data['responses']
            indices = list(response_answers.keys())
            print(f"   Question indices: {sorted(indices)}")
            
            # Count each question
            for idx in indices:
                if idx not in question_counts:
                    question_counts[idx] = 0
                question_counts[idx] += 1
                
                # Show the actual value
                value = response_answers[idx].get('value', 'N/A')
                print(f"   Q{idx}: '{value}'")
    
    print(f"\n📊 QUESTION COVERAGE SUMMARY:")
    for q_idx in sorted(question_counts.keys(), key=int):
        count = question_counts[q_idx]
        print(f"   Question {q_idx}: {count} responses")
    
    # Check which questions have no responses
    for i in range(9):  # Form has 9 questions (0-8)
        if str(i) not in question_counts:
            print(f"   Question {i}: 0 responses ❌")

if __name__ == "__main__":
    analyze_response_coverage()