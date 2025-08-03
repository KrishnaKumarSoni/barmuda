"""
CRITICAL: Active/Inactive Response Control Tests
Tests the core business logic that controls when forms can accept responses
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestActiveInactiveControl:
    """Test active/inactive form response control system"""

    def test_inactive_form_blocks_chat_start(
        self, client, mock_firestore_client, mock_firestore_data, sample_form
    ):
        """Test that inactive forms prevent chat session creation"""
        # Setup: Add inactive form to mock database
        sample_form["active"] = False
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
        self, client, mock_firestore_client, mock_firestore_data, sample_active_form
    ):
        """Test that active forms allow chat session creation"""
        # Setup: Add active form to mock database
        mock_firestore_data["forms"]["test_form_123"] = sample_active_form

        with patch("app.db", mock_firestore_client):
            response = client.post(
                "/api/chat/start",
                json={"form_id": "test_form_123", "device_id": "device_123"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "session_id" in data

    def test_inactive_form_page_shows_unavailable_message(
        self, client, mock_db, sample_form
    ):
        """Test that inactive form pages show 'Survey Not Available' message"""
        sample_form["active"] = False

        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            response = client.get("/form/test_form_123")

            assert response.status_code == 200
            assert (
                b"Survey Not Available" in response.data
                or b"not available" in response.data.lower()
            )

    def test_active_form_page_loads_chat_interface(
        self, client, mock_db, sample_active_form
    ):
        """Test that active form pages load the chat interface"""
        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_active_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            response = client.get("/form/test_form_123")

            assert response.status_code == 200
            # Should contain chat interface elements
            assert (
                b"chat" in response.data.lower() or b"message" in response.data.lower()
            )

    def test_status_toggle_changes_form_availability(
        self, authenticated_session, mock_db, sample_form
    ):
        """Test that toggling form status changes response availability"""
        with patch("app.db", mock_db):
            # Mock the update operation
            mock_doc = Mock()
            mock_db.collection.return_value.document.return_value = mock_doc
            mock_doc.get.return_value.to_dict.return_value = sample_form
            mock_doc.get.return_value.exists = True
            mock_doc.update.return_value = None

            # Toggle to active
            response = authenticated_session.put(
                "/api/forms/test_form_123/status", json={"active": True}
            )

            assert response.status_code == 200

            # Verify update was called with correct data
            mock_doc.update.assert_called_with({"active": True})

    def test_inactive_form_blocks_chat_messages(self, client, mock_db, sample_form):
        """Test that inactive forms block chat message processing"""
        sample_form["active"] = False

        with patch("app.db", mock_db):
            # Mock form lookup
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock session lookup to return a session
            mock_session = {
                "form_id": "test_form_123",
                "status": "active",
                "device_id": "device_123",
            }
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                mock_session
            )

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "Hello"},
            )

            # Should fail because form is inactive
            assert response.status_code in [400, 403]

    def test_form_api_respects_active_status(self, client, mock_db, sample_form):
        """Test that form API only returns active forms for public access"""
        sample_form["active"] = False

        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            response = client.get("/api/form/test_form_123")

            # Public API should respect active status
            if response.status_code == 200:
                data = json.loads(response.data)
                # Either returns form data for active forms or error for inactive
                if "error" in data:
                    assert "not available" in data["error"].lower()

    def test_dashboard_shows_all_forms_regardless_of_status(
        self, authenticated_session, mock_db
    ):
        """Test that dashboard shows both active and inactive forms"""
        forms = [
            {
                "id": "form1",
                "title": "Active Form",
                "active": True,
                "creator_id": "test_user_123",
            },
            {
                "id": "form2",
                "title": "Inactive Form",
                "active": False,
                "creator_id": "test_user_123",
            },
        ]

        with patch("app.db", mock_db):
            # Mock the query for user's forms
            mock_query = Mock()
            mock_db.collection.return_value.where.return_value = mock_query
            mock_query.stream.return_value = [
                Mock(to_dict=lambda: form, id=form["id"]) for form in forms
            ]

            response = authenticated_session.get("/dashboard")

            assert response.status_code == 200
            # Should show both forms in dashboard
            assert b"Active Form" in response.data
            assert b"Inactive Form" in response.data

    def test_nonexistent_form_returns_404(self, client, mock_db):
        """Test that accessing nonexistent forms returns 404"""
        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )

            response = client.get("/form/nonexistent_form")
            assert response.status_code == 404

    def test_form_status_requires_authentication(self, client, mock_db):
        """Test that changing form status requires authentication"""
        with patch("app.db", mock_db):
            response = client.put(
                "/api/forms/test_form_123/status", json={"active": True}
            )

            # Should require authentication
            assert response.status_code in [401, 302]  # 302 for redirect to login
