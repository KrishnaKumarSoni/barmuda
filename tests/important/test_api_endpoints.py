"""
IMPORTANT: API Endpoint Validation Tests
Tests all 19 API endpoints with positive and negative test cases
"""

import pytest
from unittest.mock import Mock, patch
import json


class TestAPIEndpointValidation:
    """Test validation and error handling for all API endpoints"""

    # Authentication Endpoints (4)

    def test_google_auth_missing_token(self, client):
        """Test /auth/google with missing idToken"""
        response = client.post("/auth/google", json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_google_auth_empty_token(self, client):
        """Test /auth/google with empty idToken"""
        response = client.post("/auth/google", json={"idToken": ""})
        assert response.status_code == 400

    def test_logout_without_session(self, client):
        """Test /auth/logout without active session"""
        response = client.post("/auth/logout")
        # Should handle gracefully
        assert response.status_code in [200, 400]

    def test_verify_missing_token(self, client):
        """Test /auth/verify with missing token"""
        response = client.post("/auth/verify", json={})
        assert response.status_code == 400

    def test_profile_unauthenticated(self, client):
        """Test /api/user/profile without authentication"""
        response = client.get("/api/user/profile")
        assert response.status_code in [401, 302]

    # Form Management Endpoints (7)

    def test_infer_missing_input(self, authenticated_session):
        """Test /api/infer with missing dump/template"""
        response = authenticated_session.post("/api/infer", json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_infer_empty_dump(self, authenticated_session):
        """Test /api/infer with empty dump"""
        response = authenticated_session.post("/api/infer", json={"dump": ""})
        assert response.status_code == 400

    def test_infer_invalid_template(self, authenticated_session):
        """Test /api/infer with invalid template"""
        response = authenticated_session.post(
            "/api/infer", json={"template": "nonexistent_template"}
        )
        assert response.status_code == 400

    def test_save_form_unauthenticated(self, client):
        """Test /api/save_form without authentication"""
        response = client.post("/api/save_form", json={"title": "Test"})
        assert response.status_code in [401, 302]

    def test_save_form_missing_required_fields(self, authenticated_session):
        """Test /api/save_form with missing required fields"""
        response = authenticated_session.post("/api/save_form", json={})
        assert response.status_code == 400

        # Missing title
        response = authenticated_session.post("/api/save_form", json={"questions": []})
        assert response.status_code == 400

        # Missing questions
        response = authenticated_session.post("/api/save_form", json={"title": "Test"})
        assert response.status_code == 400

    def test_save_form_invalid_questions(self, authenticated_session):
        """Test /api/save_form with invalid question structure"""
        invalid_questions = [
            # Missing required fields
            {"type": "text"},  # Missing text
            {"text": "Question"},  # Missing type
            {"text": "Question", "type": "invalid_type"},  # Invalid type
            {
                "text": "Question",
                "type": "multiple_choice",
            },  # Missing options for multiple_choice
        ]

        for invalid_question in invalid_questions:
            response = authenticated_session.post(
                "/api/save_form",
                json={"title": "Test", "questions": [invalid_question]},
            )
            assert response.status_code == 400

    def test_update_form_nonexistent(self, authenticated_session):
        """Test /api/update_form with nonexistent form"""
        with patch("app.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )

            response = authenticated_session.put(
                "/api/update_form/nonexistent", json={"title": "Test", "questions": []}
            )
            assert response.status_code == 404

    def test_update_form_wrong_owner(self, authenticated_session, mock_db, sample_form):
        """Test /api/update_form with wrong owner"""
        sample_form["creator_id"] = "other_user"

        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            response = authenticated_session.put(
                "/api/update_form/test_form_123",
                json={"title": "Test", "questions": []},
            )
            assert response.status_code == 403

    def test_form_api_nonexistent_form(self, client):
        """Test /api/form/<form_id> with nonexistent form"""
        with patch("app.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )

            response = client.get("/api/form/nonexistent")
            assert response.status_code == 404

    def test_health_endpoint(self, client):
        """Test /api/health endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "status" in data
        assert data["status"] == "healthy"

    def test_form_status_invalid_data(
        self, authenticated_session, mock_db, sample_form
    ):
        """Test /api/forms/<form_id>/status with invalid data"""
        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Missing active field
            response = authenticated_session.put(
                "/api/forms/test_form_123/status", json={}
            )
            assert response.status_code == 400

            # Invalid active value
            response = authenticated_session.put(
                "/api/forms/test_form_123/status", json={"active": "not_boolean"}
            )
            assert response.status_code == 400

    def test_delete_form_nonexistent(self, authenticated_session):
        """Test /api/forms/<form_id> DELETE with nonexistent form"""
        with patch("app.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )

            response = authenticated_session.delete("/api/forms/nonexistent")
            assert response.status_code == 404

    # Chat Interface Endpoints (3)

    def test_chat_start_missing_fields(self, client):
        """Test /api/chat/start with missing required fields"""
        # Missing form_id
        response = client.post("/api/chat/start", json={"device_id": "device_123"})
        assert response.status_code == 400

        # Missing device_id
        response = client.post("/api/chat/start", json={"form_id": "form_123"})
        assert response.status_code == 400

        # Empty form_id
        response = client.post(
            "/api/chat/start", json={"form_id": "", "device_id": "device_123"}
        )
        assert response.status_code == 400

    def test_chat_start_nonexistent_form(self, client):
        """Test /api/chat/start with nonexistent form"""
        with patch("app.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )

            response = client.post(
                "/api/chat/start",
                json={"form_id": "nonexistent", "device_id": "device_123"},
            )
            assert response.status_code == 404

    def test_chat_message_missing_fields(self, client):
        """Test /api/chat/message with missing fields"""
        # Missing session_id
        response = client.post("/api/chat/message", json={"message": "Hello"})
        assert response.status_code == 400

        # Missing message
        response = client.post("/api/chat/message", json={"session_id": "session_123"})
        assert response.status_code == 400

        # Empty message
        response = client.post(
            "/api/chat/message", json={"session_id": "session_123", "message": ""}
        )
        assert response.status_code == 400

    def test_chat_message_nonexistent_session(self, client):
        """Test /api/chat/message with nonexistent session"""
        with patch("app.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )

            response = client.post(
                "/api/chat/message",
                json={"session_id": "nonexistent", "message": "Hello"},
            )
            assert response.status_code == 404

    def test_chat_status_nonexistent_session(self, client):
        """Test /api/chat/status/<session_id> with nonexistent session"""
        with patch("app.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )

            response = client.get("/api/chat/status/nonexistent")
            assert response.status_code == 404

    # Response Management Endpoints (4)

    def test_responses_unauthenticated(self, client):
        """Test /api/responses/<form_id> without authentication"""
        response = client.get("/api/responses/form_123")
        assert response.status_code in [401, 302]

    def test_responses_nonexistent_form(self, authenticated_session):
        """Test /api/responses/<form_id> with nonexistent form"""
        with patch("app.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )

            response = authenticated_session.get("/api/responses/nonexistent")
            assert response.status_code == 404

    def test_responses_wrong_owner(self, authenticated_session, mock_db, sample_form):
        """Test /api/responses/<form_id> with wrong owner"""
        sample_form["creator_id"] = "other_user"

        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            response = authenticated_session.get("/api/responses/test_form_123")
            assert response.status_code == 403

    def test_wordcloud_invalid_question_index(
        self, authenticated_session, mock_db, sample_form
    ):
        """Test /api/wordcloud/<form_id>/<question_index> with invalid index"""
        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Index out of range
            response = authenticated_session.get("/api/wordcloud/test_form_123/999")
            assert response.status_code == 400

            # Negative index
            response = authenticated_session.get("/api/wordcloud/test_form_123/-1")
            assert response.status_code == 400

    def test_export_invalid_format(self, authenticated_session, mock_db, sample_form):
        """Test /api/export/<form_id>/<format> with invalid format"""
        with patch("app.db", mock_db):
            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            response = authenticated_session.get(
                "/api/export/test_form_123/invalid_format"
            )
            assert response.status_code == 400

    def test_export_unauthenticated(self, client):
        """Test /api/export/<form_id>/<format> without authentication"""
        response = client.get("/api/export/form_123/csv")
        assert response.status_code in [401, 302]

    # Frontend Routes (2)

    def test_dashboard_unauthenticated(self, client):
        """Test /dashboard without authentication"""
        response = client.get("/dashboard")
        assert response.status_code in [401, 302]

    def test_create_form_unauthenticated(self, client):
        """Test /create-form without authentication"""
        response = client.get("/create-form")
        assert response.status_code in [401, 302]

    def test_edit_form_unauthenticated(self, client):
        """Test /edit-form without authentication"""
        response = client.get("/edit-form?id=form_123")
        assert response.status_code in [401, 302]

    def test_responses_page_unauthenticated(self, client):
        """Test /responses/<form_id> without authentication"""
        response = client.get("/responses/form_123")
        assert response.status_code in [401, 302]

    # Error Handling and Edge Cases

    def test_invalid_json_request(self, authenticated_session):
        """Test endpoints with invalid JSON"""
        response = authenticated_session.post(
            "/api/infer", data="invalid json", content_type="application/json"
        )
        assert response.status_code == 400

    def test_oversized_request(self, authenticated_session):
        """Test endpoints with oversized request data"""
        large_dump = "x" * 100000  # 100KB dump
        response = authenticated_session.post("/api/infer", json={"dump": large_dump})
        # Should either accept or reject gracefully
        assert response.status_code in [200, 400, 413]

    def test_sql_injection_attempts(self, authenticated_session):
        """Test endpoints with SQL injection attempts"""
        malicious_inputs = [
            "'; DROP TABLE forms; --",
            "1' OR '1'='1",
            "<script>alert('xss')</script>",
        ]

        for malicious_input in malicious_inputs:
            response = authenticated_session.post(
                "/api/infer", json={"dump": malicious_input}
            )
            # Should handle safely
            assert response.status_code in [200, 400]

    def test_concurrent_requests(self, authenticated_session, mock_db):
        """Test handling of concurrent requests to same endpoint"""
        with patch("app.db", mock_db), patch("app.openai_client") as mock_openai:

            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps({"title": "Test", "questions": []})
            mock_db.collection.return_value.add.return_value = (None, "test_123")

            # Multiple rapid requests
            responses = []
            for i in range(5):
                response = authenticated_session.post(
                    "/api/infer", json={"dump": f"Test form {i}"}
                )
                responses.append(response)

            # All should succeed or fail gracefully
            for response in responses:
                assert response.status_code in [200, 429, 500]

    def test_method_not_allowed(self, client):
        """Test endpoints with wrong HTTP methods"""
        # GET on POST-only endpoints
        response = client.get("/api/infer")
        assert response.status_code == 405

        response = client.get("/api/save_form")
        assert response.status_code == 405

        # POST on GET-only endpoints
        response = client.post("/api/health")
        assert response.status_code == 405

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/api/health")
        # Should have CORS headers or handle OPTIONS appropriately
        assert response.status_code in [200, 204]

    def test_rate_limiting_simulation(self, client):
        """Test rate limiting behavior (if implemented)"""
        # Make many requests rapidly
        responses = []
        for i in range(100):
            response = client.post(
                "/api/chat/start", json={"form_id": "test", "device_id": f"device_{i}"}
            )
            responses.append(response.status_code)

        # Should see some rate limiting (429) or all succeed
        status_codes = set(responses)
        # Either all fail due to other validation or some rate limited
        assert 429 in status_codes or all(code in [400, 404] for code in status_codes)
