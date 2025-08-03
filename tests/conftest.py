"""
Test configuration and fixtures for Bermuda test suite
"""

import os
import pytest
import tempfile
import json
from unittest.mock import Mock, patch
from flask import Flask
from faker import Faker

# Set test environment
os.environ["TESTING"] = "true"
os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"

fake = Faker()


@pytest.fixture(scope="session")
def app():
    """Create application for testing"""
    # Mock Firebase before importing app
    with patch("firebase_admin.initialize_app"), patch(
        "firebase_admin.credentials.Certificate"
    ), patch("firebase_admin.firestore.client"), patch("openai.OpenAI"):

        from app import app as flask_app

        flask_app.config["TESTING"] = True
        flask_app.config["WTF_CSRF_ENABLED"] = False
        return flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def mock_db():
    """Mock Firestore database"""
    return Mock()


@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    return Mock()


@pytest.fixture
def sample_form():
    """Sample form data for testing"""
    return {
        "id": "test_form_123",
        "title": "Customer Feedback Survey",
        "description": "Tell us about your experience",
        "creator_id": "user_123",
        "active": False,
        "created_at": "2025-01-01T00:00:00Z",
        "questions": [
            {
                "text": "How satisfied are you with our service?",
                "type": "rating",
                "enabled": True,
                "options": ["1", "2", "3", "4", "5"],
            },
            {"text": "What could we improve?", "type": "text", "enabled": True},
        ],
        "demographics": {
            "enabled": True,
            "age": {"enabled": True},
            "gender": {"enabled": True},
        },
    }


@pytest.fixture
def sample_active_form(sample_form):
    """Sample active form"""
    form = sample_form.copy()
    form["active"] = True
    return form


@pytest.fixture
def sample_chat_session():
    """Sample chat session data"""
    return {
        "session_id": "session_123",
        "form_id": "test_form_123",
        "device_id": "device_123",
        "location": {"country": "US", "city": "San Francisco"},
        "started_at": "2025-01-01T00:00:00Z",
        "status": "active",
        "message_count": 3,
        "responses": {
            "0": {"answer": "4", "question": "How satisfied are you with our service?"},
            "1": {
                "answer": "More features please",
                "question": "What could we improve?",
            },
        },
    }


@pytest.fixture
def sample_responses():
    """Sample response data for testing"""
    return [
        {
            "session_id": "session_1",
            "device_id": "device_1",
            "responses": {"0": "5", "1": "Great service!"},
            "metadata": {"partial": False, "completed_at": "2025-01-01T00:00:00Z"},
        },
        {
            "session_id": "session_2",
            "device_id": "device_2",
            "responses": {"0": "3", "1": "Could be better"},
            "metadata": {"partial": False, "completed_at": "2025-01-01T01:00:00Z"},
        },
    ]


@pytest.fixture
def authenticated_session(client):
    """Create authenticated session"""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["user_id"] = "test_user_123"
        sess["email"] = "test@example.com"
    return client


@pytest.fixture
def edge_case_messages():
    """Edge case chat messages for testing"""
    return {
        "off_topic": [
            "What's the weather like?",
            "Tell me about bananas",
            "I like cats",
        ],
        "skip_requests": ["Skip this question", "I don't want to answer", "Pass"],
        "multi_answers": [
            "Alex, 25, from LA",
            "I'm 30 and work as an engineer in New York",
        ],
        "conflicting": ["Yes, I love it", "Actually, no I don't"],
        "vague": ["meh", "kinda", "not really sure"],
    }
