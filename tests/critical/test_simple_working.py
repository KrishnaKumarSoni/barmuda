"""
Simple working tests to verify the test infrastructure is working
"""

import json
from unittest.mock import patch


class TestSimpleWorking:
    """Test that our test infrastructure is working properly"""

    def test_inactive_form_blocks_chat_start(
        self, client, mock_firestore_client, mock_firestore_data
    ):
        """Test that inactive forms prevent chat session creation"""
        # Setup: Add inactive form to mock database
        sample_form = {
            "id": "test_form_123",
            "title": "Test Form",
            "active": False,
            "creator_id": "user_123",
            "questions": [{"text": "Test question", "type": "text", "enabled": True}],
        }
        mock_firestore_data["forms"]["test_form_123"] = sample_form

        with patch("app.db", mock_firestore_client):
            response = client.post(
                "/api/chat/start",
                json={"form_id": "test_form_123", "device_id": "device_123"},
            )

            assert response.status_code == 403
            data = json.loads(response.data)
            assert "not available" in data["error"].lower()

    def test_active_form_allows_chat_start(
        self, client, mock_firestore_client, mock_firestore_data
    ):
        """Test that active forms allow chat session creation"""
        # Setup: Add active form to mock database
        sample_form = {
            "id": "test_form_123",
            "title": "Test Form",
            "active": True,
            "creator_id": "user_123",
            "questions": [{"text": "Test question", "type": "text", "enabled": True}],
        }
        mock_firestore_data["forms"]["test_form_123"] = sample_form

        with patch("app.db", mock_firestore_client):
            response = client.post(
                "/api/chat/start",
                json={"form_id": "test_form_123", "device_id": "device_123"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "session_id" in data
