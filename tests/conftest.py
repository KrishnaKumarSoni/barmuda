"""
Test configuration and fixtures for Barmuda test suite
"""

import json
import os
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest
from faker import Faker
from flask import Flask

# Set test environment BEFORE any imports
os.environ["TESTING"] = "true"
os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"

# Apply global Firebase mocks BEFORE app import
firebase_mock_patcher = patch("firebase_admin.initialize_app")
firestore_mock_patcher = patch("firebase_admin.firestore.client")
credentials_mock_patcher = patch("firebase_admin.credentials.Certificate")
openai_mock_patcher = patch("openai.OpenAI")

# Start the global mocks
firebase_mock_patcher.start()
credentials_mock_patcher.start()

# Mock firestore client to return our mock
mock_firestore_instance = Mock()
firestore_mock_patcher.start()
firestore_mock_patcher.return_value = mock_firestore_instance

# Mock OpenAI
mock_openai_instance = Mock()
mock_openai_instance.chat.completions.create.return_value = Mock(
    choices=[Mock(message=Mock(content='{"test": "response"}'))]
)
openai_mock_patcher.start()
openai_mock_patcher.return_value = mock_openai_instance

fake = Faker()


@pytest.fixture(scope="session")
def app():
    """Create application for testing"""
    # Import app after global mocks are applied
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["SECRET_KEY"] = "test-secret-key"

    return flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def mock_firestore_data():
    """In-memory Firestore data for testing"""
    return {
        "forms": {},
        "users": {},
        "chat_sessions": {},
        "responses": {},
    }


@pytest.fixture
def mock_firestore_client(mock_firestore_data):
    """Mock Firestore client that uses Mock objects with in-memory data"""
    
    def create_mock_document(data_store, collection_name, doc_id):
        mock_doc = Mock()
        
        def mock_get():
            doc_data = data_store[collection_name].get(doc_id)
            result = Mock()
            result.exists = doc_data is not None
            result.to_dict = Mock(return_value=doc_data if doc_data else {})
            return result
        
        def mock_set(data):
            data_store[collection_name][doc_id] = data
            return Mock()  # Return mock for chaining
        
        def mock_update(data):
            if doc_id in data_store[collection_name]:
                data_store[collection_name][doc_id].update(data)
            else:
                data_store[collection_name][doc_id] = data
            return Mock()  # Return mock for chaining
        
        def mock_delete():
            if doc_id in data_store[collection_name]:
                del data_store[collection_name][doc_id]
            return Mock()  # Return mock for chaining
        
        mock_doc.get = Mock(side_effect=mock_get)
        mock_doc.set = Mock(side_effect=mock_set)
        mock_doc.update = Mock(side_effect=mock_update)
        mock_doc.delete = Mock(side_effect=mock_delete)
        
        return mock_doc
    
    def create_mock_collection(data_store, collection_name):
        mock_collection = Mock()
        
        def mock_document(doc_id):
            return create_mock_document(data_store, collection_name, doc_id)
        
        def mock_where(field, op, value):
            # Simple query implementation
            result = Mock()
            matching_docs = []
            
            for doc_id, doc_data in data_store[collection_name].items():
                if field in doc_data:
                    if op == "==" and doc_data[field] == value:
                        mock_doc_ref = Mock()
                        mock_doc_ref.id = doc_id
                        mock_doc_ref.to_dict = Mock(return_value=doc_data)
                        matching_docs.append(mock_doc_ref)
            
            result.stream = Mock(return_value=matching_docs)
            return result
        
        def mock_add(data):
            import uuid
            doc_id = str(uuid.uuid4())
            data_store[collection_name][doc_id] = data
            return (None, doc_id)  # Return tuple as expected
        
        mock_collection.document = Mock(side_effect=mock_document)
        mock_collection.where = Mock(side_effect=mock_where)
        mock_collection.add = Mock(side_effect=mock_add)
        
        return mock_collection
    
    mock_db = Mock()
    
    def mock_collection(collection_name):
        return create_mock_collection(mock_firestore_data, collection_name)
    
    mock_db.collection = Mock(side_effect=mock_collection)
    
    return mock_db


# Cleanup function for global mocks
def pytest_sessionfinish(session, exitstatus):
    """Clean up global mocks after test session"""
    firebase_mock_patcher.stop()
    firestore_mock_patcher.stop()
    credentials_mock_patcher.stop()
    openai_mock_patcher.stop()


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
