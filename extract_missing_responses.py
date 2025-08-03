#!/usr/bin/env python3
"""
Extract responses from chat sessions that have data but weren't processed
"""

import firebase_admin
from firebase_admin import credentials, firestore

from data_extraction import extract_chat_responses

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("bermuda-01-firebase-adminsdk-fbsvc-660474f630.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()


def extract_all_sessions(form_id):
    """Extract responses from all chat sessions with data"""
    print(f"🔍 Finding chat sessions for form: {form_id}")

    # Get all chat sessions for this form
    sessions = list(
        db.collection("chat_sessions").where("form_id", "==", form_id).stream()
    )
    print(f"Found {len(sessions)} total chat sessions")

    # Get existing extracted responses to avoid duplicates
    existing_responses = set()
    responses = list(
        db.collection("responses").where("form_id", "==", form_id).stream()
    )
    for response in responses:
        response_data = response.to_dict()
        session_id = response_data.get("session_id")
        if session_id:
            existing_responses.add(session_id)

    print(f"Found {len(existing_responses)} already extracted responses")

    # Process sessions with responses that haven't been extracted
    extracted_count = 0
    skipped_count = 0

    for session in sessions:
        session_id = session.id
        session_data = session.to_dict()

        # Skip if already extracted
        if session_id in existing_responses:
            skipped_count += 1
            continue

        # Check if session has responses
        responses_data = session_data.get("responses", {})
        if not responses_data:
            skipped_count += 1
            continue

        print(f"\n📊 Extracting from session: {session_id}")
        print(f"   Responses collected: {len(responses_data)}")

        try:
            result = extract_chat_responses(session_id)
            if result.get("success"):
                print(f"   ✅ Extracted to response ID: {result.get('response_id')}")
                extracted_count += 1
            else:
                print(f"   ❌ Extraction failed: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ Extraction error: {e}")

    print(f"\n🎉 SUMMARY:")
    print(f"   ✅ Successfully extracted: {extracted_count}")
    print(f"   ⏭️  Skipped (no data or already extracted): {skipped_count}")
    print(
        f"   📊 Total responses in collection: {len(existing_responses) + extracted_count}"
    )


if __name__ == "__main__":
    FORM_ID = "x4GZrJ1165MiMze4YC2Y"
    extract_all_sessions(FORM_ID)
