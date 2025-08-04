#!/usr/bin/env python3
"""
Generate test responses for form aggregation testing
"""

import json
import random
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("bermuda-01-firebase-adminsdk-fbsvc-660474f630.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Form ID to add responses to
FORM_ID = "x4GZrJ1165MiMze4YC2Y"

# Sample responses for different question types
sample_responses = [
    {
        "responses": {
            "0": {
                "value": "I prefer saving articles using browser bookmarks",
                "timestamp": "2025-08-02T09:10:15.123Z",
            },
            "1": {"value": "Daily", "timestamp": "2025-08-02T09:10:20.456Z"},
            "2": {"value": "3", "timestamp": "2025-08-02T09:10:25.789Z"},
            "3": {
                "value": "Readability and organization",
                "timestamp": "2025-08-02T09:10:30.012Z",
            },
            "4": {"value": "4", "timestamp": "2025-08-02T09:10:35.345Z"},
            "5": {"value": "Reading", "timestamp": "2025-08-02T09:10:40.678Z"},
            "6": {"value": "25-34", "timestamp": "2025-08-02T09:10:45.901Z"},
            "7": {"value": "College graduate", "timestamp": "2025-08-02T09:10:50.234Z"},
            "8": {"value": "Technology", "timestamp": "2025-08-02T09:10:55.567Z"},
        },
        "partial": False,
        "device_id": "test-device-001",
        "metadata": {
            "start_time": "2025-08-02T09:10:10.000Z",
            "end_time": "2025-08-02T09:11:00.000Z",
            "chat_length": 18,
        },
    },
    {
        "responses": {
            "0": {
                "value": "I use Notion to save and organize content",
                "timestamp": "2025-08-02T09:15:15.123Z",
            },
            "1": {"value": "Weekly", "timestamp": "2025-08-02T09:15:20.456Z"},
            "2": {"value": "5", "timestamp": "2025-08-02T09:15:25.789Z"},
            "3": {
                "value": "Cross-platform sync and search functionality",
                "timestamp": "2025-08-02T09:15:30.012Z",
            },
            "4": {"value": "5", "timestamp": "2025-08-02T09:15:35.345Z"},
            "5": {"value": "Productivity", "timestamp": "2025-08-02T09:15:40.678Z"},
            "6": {"value": "35-44", "timestamp": "2025-08-02T09:15:45.901Z"},
            "7": {"value": "College graduate", "timestamp": "2025-08-02T09:15:50.234Z"},
            "8": {"value": "Marketing", "timestamp": "2025-08-02T09:15:55.567Z"},
        },
        "partial": False,
        "device_id": "test-device-002",
        "metadata": {
            "start_time": "2025-08-02T09:15:10.000Z",
            "end_time": "2025-08-02T09:16:00.000Z",
            "chat_length": 16,
        },
    },
    {
        "responses": {
            "0": {
                "value": "Pocket for saving articles",
                "timestamp": "2025-08-02T09:20:15.123Z",
            },
            "1": {"value": "Daily", "timestamp": "2025-08-02T09:20:20.456Z"},
            "2": {"value": "2", "timestamp": "2025-08-02T09:20:25.789Z"},
            "3": {
                "value": "Offline reading capability",
                "timestamp": "2025-08-02T09:20:30.012Z",
            },
            "4": {"value": "3", "timestamp": "2025-08-02T09:20:35.345Z"},
            "5": {"value": "Technology", "timestamp": "2025-08-02T09:20:40.678Z"},
            "6": {"value": "18-24", "timestamp": "2025-08-02T09:20:45.901Z"},
            "7": {"value": "Some college", "timestamp": "2025-08-02T09:20:50.234Z"},
            "8": {"value": "Student", "timestamp": "2025-08-02T09:20:55.567Z"},
        },
        "partial": False,
        "device_id": "test-device-003",
        "metadata": {
            "start_time": "2025-08-02T09:20:10.000Z",
            "end_time": "2025-08-02T09:21:00.000Z",
            "chat_length": 14,
        },
    },
    {
        "responses": {
            "0": {
                "value": "Screenshots and photos",
                "timestamp": "2025-08-02T09:25:15.123Z",
            },
            "1": {"value": "Monthly", "timestamp": "2025-08-02T09:25:20.456Z"},
            "2": {"value": "1", "timestamp": "2025-08-02T09:25:25.789Z"},
            "3": {
                "value": "Quick and easy to access",
                "timestamp": "2025-08-02T09:25:30.012Z",
            },
            "4": {"value": "2", "timestamp": "2025-08-02T09:25:35.345Z"},
            "5": {"value": "Entertainment", "timestamp": "2025-08-02T09:25:40.678Z"},
            "6": {"value": "45-54", "timestamp": "2025-08-02T09:25:45.901Z"},
            "7": {"value": "High school", "timestamp": "2025-08-02T09:25:50.234Z"},
            "8": {"value": "Healthcare", "timestamp": "2025-08-02T09:25:55.567Z"},
        },
        "partial": False,
        "device_id": "test-device-004",
        "metadata": {
            "start_time": "2025-08-02T09:25:10.000Z",
            "end_time": "2025-08-02T09:26:00.000Z",
            "chat_length": 12,
        },
    },
    {
        "responses": {
            "0": {
                "value": "OneNote for everything",
                "timestamp": "2025-08-02T09:30:15.123Z",
            },
            "1": {"value": "Weekly", "timestamp": "2025-08-02T09:30:20.456Z"},
            "2": {"value": "4", "timestamp": "2025-08-02T09:30:25.789Z"},
            "3": {"value": "[SKIP]", "timestamp": "2025-08-02T09:30:30.012Z"},
            "4": {"value": "4", "timestamp": "2025-08-02T09:30:35.345Z"},
            "5": {"value": "Business", "timestamp": "2025-08-02T09:30:40.678Z"},
            "6": {"value": "25-34", "timestamp": "2025-08-02T09:30:45.901Z"},
            "7": {"value": "Graduate degree", "timestamp": "2025-08-02T09:30:50.234Z"},
            "8": {"value": "Finance", "timestamp": "2025-08-02T09:30:55.567Z"},
        },
        "partial": False,
        "device_id": "test-device-005",
        "metadata": {
            "start_time": "2025-08-02T09:30:10.000Z",
            "end_time": "2025-08-02T09:31:00.000Z",
            "chat_length": 15,
        },
    },
    {
        "responses": {
            "0": {
                "value": "I just bookmark things randomly",
                "timestamp": "2025-08-02T09:35:15.123Z",
            },
            "1": {"value": "Daily", "timestamp": "2025-08-02T09:35:20.456Z"},
            "2": {"value": "[SKIP]", "timestamp": "2025-08-02T09:35:25.789Z"},
            "3": {
                "value": "Don't really think about it",
                "timestamp": "2025-08-02T09:35:30.012Z",
            },
            "4": {"value": "1", "timestamp": "2025-08-02T09:35:35.345Z"},
            "5": {"value": "News", "timestamp": "2025-08-02T09:35:40.678Z"},
            "6": {"value": "55+", "timestamp": "2025-08-02T09:35:45.901Z"},
            "7": {"value": "High school", "timestamp": "2025-08-02T09:35:50.234Z"},
            "8": {"value": "Retail", "timestamp": "2025-08-02T09:35:55.567Z"},
        },
        "partial": True,  # This one was abandoned early
        "device_id": "test-device-006",
        "metadata": {
            "start_time": "2025-08-02T09:35:10.000Z",
            "end_time": "2025-08-02T09:36:30.000Z",
            "chat_length": 20,
            "end_reason": "timeout",
        },
    },
]


def generate_responses():
    """Generate test responses in Firestore"""

    for i, response_data in enumerate(sample_responses):
        # Generate session ID
        session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:03d}"

        # Create response document
        response_doc = {
            "session_id": session_id,
            "form_id": FORM_ID,
            "responses": response_data["responses"],
            "partial": response_data["partial"],
            "device_id": response_data["device_id"],
            "created_at": datetime.now().isoformat(),
            "metadata": response_data["metadata"],
        }

        # Add to Firestore
        db.collection("responses").document(session_id).set(response_doc)
        print(f"✅ Created response {i+1}: {session_id}")


if __name__ == "__main__":
    print("🚀 Generating test responses for form aggregation...")
    generate_responses()
    print("✅ Test responses generated successfully!")
    print(f"📊 View responses at: https://barmuda-kappa.vercel.app/responses/{FORM_ID}")
