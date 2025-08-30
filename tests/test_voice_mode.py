"""Tests for voice mode functionality"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

@patch('app.verify_firebase_token')
@patch('app.db')
def test_voice_settings_validation(mock_db, mock_verify, app, client):
    """Test voice settings validation in form creation"""
    
    # Mock auth and firestore
    mock_verify.return_value = {'uid': 'test_user'}
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    
    # Test invalid mode
    form_data = {
        "title": "Test Voice Form",
        "questions": [{"text": "How are you?", "type": "text", "enabled": True}],
        "mode": "invalid_mode"
    }
    
    response = client.post('/api/save_form', 
                          json=form_data,
                          headers={'Authorization': 'Bearer mock_token'})
    
    assert response.status_code == 400
    data = response.get_json()
    assert "Invalid mode" in data["error"]


@patch('app.verify_firebase_token')  
@patch('app.db')
def test_voice_settings_required_fields(mock_db, mock_verify, app, client):
    """Test that voice mode requires all voice settings"""
    
    # Mock auth and firestore
    mock_verify.return_value = {'uid': 'test_user'}
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    
    # Missing voice settings
    form_data = {
        "title": "Test Voice Form", 
        "questions": [{"text": "How are you?", "type": "text", "enabled": True}],
        "mode": "voice"
    }
    
    response = client.post('/api/save_form',
                          json=form_data, 
                          headers={'Authorization': 'Bearer mock_token'})
    
    assert response.status_code == 400
    data = response.get_json()
    assert "Voice settings" in data["error"]
    
    # Missing agent_id
    form_data["voice_settings"] = {
        "language": "en",
        "voice_id": "test_voice"
    }
    
    response = client.post('/api/save_form',
                          json=form_data,
                          headers={'Authorization': 'Bearer mock_token'})
                          
    assert response.status_code == 400
    data = response.get_json()
    assert "agent_id" in data["error"]


@patch('app.create_ephemeral_token')
def test_voice_token_generation_security(mock_token, app, client):
    """Test voice token generation with form ownership verification"""
    
    # Test missing form_id
    response = client.post('/api/voice/token', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "form_id required" in data["error"]
    
    # Test non-existent form
    response = client.post('/api/voice/token', json={"form_id": "nonexistent"})
    assert response.status_code == 404


def test_voice_session_start_validation(app, client):
    """Test voice session start validation"""
    
    # Test missing form_id
    response = client.post('/api/voice/session/start', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "form_id is required" in data["error"]
    
    # Test non-existent form
    response = client.post('/api/voice/session/start', 
                          json={"form_id": "nonexistent", "device_id": "test"})
    assert response.status_code == 404


def test_voice_session_save_validation(app, client):
    """Test voice session save validation"""
    
    # Test missing required fields
    response = client.post('/api/voice/session/save', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "session_id and form_id required" in data["error"]


def test_voice_mode_validation_deduplication(app):
    """Test that validation logic is properly deduplicated"""
    from app import validate_mode_and_voice_settings
    
    with app.app_context():
        # Test chat mode (should pass)
        result = validate_mode_and_voice_settings("chat", {})
        assert result is None
        
        # Test invalid mode
        result = validate_mode_and_voice_settings("invalid", {})
        assert result is not None
        assert result[1] == 400
        
        # Test voice mode without settings
        result = validate_mode_and_voice_settings("voice", {})
        assert result is not None
        assert result[1] == 400
        
        # Test voice mode with incomplete settings
        result = validate_mode_and_voice_settings("voice", {"language": "en"})
        assert result is not None
        assert result[1] == 400
        
        # Test voice mode with complete settings
        voice_settings = {
            "language": "en",
            "voice_id": "test_voice", 
            "agent_id": "test_agent"
        }
        result = validate_mode_and_voice_settings("voice", voice_settings)
        assert result is None


def test_voice_response_extraction(app):
    """Test voice response extraction functionality"""
    from app import extract_voice_responses
    
    # Mock transcript
    transcript = [
        {"speaker": "Agent", "text": "What's your name?"},
        {"speaker": "User", "text": "My name is John"},
        {"speaker": "Agent", "text": "How old are you?"},
        {"speaker": "User", "text": "I'm 25 years old"}
    ]
    
    # Mock form data
    form_data = {
        "questions": [
            {"text": "What's your name?", "type": "text"},
            {"text": "How old are you?", "type": "number"}
        ]
    }
    
    with patch('app.openai_client.chat.completions.create') as mock_openai:
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "John",
            "age": 25
        })
        mock_openai.return_value = mock_response
        
        result = extract_voice_responses(transcript, form_data)
        
        assert result is not None
        assert isinstance(result, dict)
        mock_openai.assert_called_once()


@pytest.fixture
def app():
    """Create test Flask app"""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture  
def client(app):
    """Create test client"""
    return app.test_client()