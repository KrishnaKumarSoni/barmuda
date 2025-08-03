"""
CRITICAL: Authentication Flow Tests
Tests the security foundation of the application
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestAuthenticationFlow:
    """Test authentication and authorization flows"""

    def test_google_auth_with_valid_token(self, client, mock_firestore_client):
        """Test successful Google authentication with valid token"""
        mock_user_data = {
            "uid": "google_user_123",
            "email": "test@example.com",
            "name": "Test User",
        }

        with (
            patch("firebase_admin.auth.verify_id_token") as mock_verify,
            patch("app.db", mock_firestore_client),
        ):

            mock_verify.return_value = mock_user_data
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )
            mock_firestore_client.collection.return_value.document.return_value.set.return_value = (
                None
            )

            response = client.post(
                "/auth/google", json={"idToken": "valid_google_token"}
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "user" in data

            # Verify user creation in database
            mock_firestore_client.collection.assert_called_with("users")

    def test_google_auth_with_invalid_token(self, client):
        """Test Google authentication with invalid token"""
        with patch("firebase_admin.auth.verify_id_token") as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            response = client.post("/auth/google", json={"idToken": "invalid_token"})

            assert response.status_code == 401
            data = json.loads(response.data)
            assert "error" in data

    def test_google_auth_creates_new_user_profile(self, client, mock_firestore_client):
        """Test that new users get profiles created"""
        mock_user_data = {
            "uid": "new_user_123",
            "email": "newuser@example.com",
            "name": "New User",
        }

        with (
            patch("firebase_admin.auth.verify_id_token") as mock_verify,
            patch("app.db", mock_firestore_client),
        ):

            mock_verify.return_value = mock_user_data
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )
            mock_firestore_client.collection.return_value.document.return_value.set.return_value = (
                None
            )

            response = client.post("/auth/google", json={"idToken": "valid_token"})

            assert response.status_code == 200

            # Verify profile creation
            mock_firestore_client.collection.return_value.document.return_value.set.assert_called_once()
            call_args = (
                mock_firestore_client.collection.return_value.document.return_value.set.call_args[0][
                    0
                ]
            )
            assert call_args["email"] == "newuser@example.com"
            assert "created_at" in call_args

    def test_google_auth_retrieves_existing_user(self, client, mock_firestore_client):
        """Test that existing users are retrieved, not recreated"""
        mock_user_data = {"uid": "existing_user_123", "email": "existing@example.com"}

        existing_profile = {
            "email": "existing@example.com",
            "created_at": "2024-01-01T00:00:00Z",
        }

        with (
            patch("firebase_admin.auth.verify_id_token") as mock_verify,
            patch("app.db", mock_firestore_client),
        ):

            mock_verify.return_value = mock_user_data
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                existing_profile
            )

            response = client.post("/auth/google", json={"idToken": "valid_token"})

            assert response.status_code == 200

            # Should NOT create new profile
            mock_firestore_client.collection.return_value.document.return_value.set.assert_not_called()

    def test_session_creation_after_auth(self, client, mock_firestore_client):
        """Test that session is properly created after authentication"""
        mock_user_data = {"uid": "user_123", "email": "test@example.com"}

        with (
            patch("firebase_admin.auth.verify_id_token") as mock_verify,
            patch("app.db", mock_firestore_client),
        ):

            mock_verify.return_value = mock_user_data
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )
            mock_firestore_client.collection.return_value.document.return_value.set.return_value = (
                None
            )

            response = client.post("/auth/google", json={"idToken": "valid_token"})

            assert response.status_code == 200

            # Test that session is created by accessing protected route
            with client.session_transaction() as sess:
                assert sess.get("authenticated") is True
                assert sess.get("user_id") == "user_123"
                assert sess.get("email") == "test@example.com"

    def test_logout_clears_session(self, authenticated_session):
        """Test that logout properly clears the session"""
        # Verify session exists
        with authenticated_session.session_transaction() as sess:
            assert sess.get("authenticated") is True

        response = authenticated_session.post("/auth/logout")
        assert response.status_code == 200

        # Verify session is cleared
        with authenticated_session.session_transaction() as sess:
            assert sess.get("authenticated") is None
            assert sess.get("user_id") is None

    def test_protected_routes_require_authentication(self, client):
        """Test that protected routes require authentication"""
        protected_routes = [
            "/dashboard",
            "/create-form",
            "/edit-form",
            "/api/save_form",
            "/api/infer",
        ]

        for route in protected_routes:
            if route == "/api/save_form" or route == "/api/infer":
                response = client.post(route, json={})
            else:
                response = client.get(route)

            # Should redirect to login or return 401
            assert response.status_code in [401, 302]

    def test_protected_routes_allow_authenticated_users(
        self, authenticated_session, mock_firestore_client
    ):
        """Test that authenticated users can access protected routes"""
        with patch("app.db", mock_firestore_client):
            # Mock database responses for dashboard
            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = []

            response = authenticated_session.get("/dashboard")
            assert response.status_code == 200

    def test_token_verification_endpoint(self, client, mock_firestore_client):
        """Test the token verification endpoint"""
        mock_user_data = {"uid": "user_123", "email": "test@example.com"}

        with (
            patch("firebase_admin.auth.verify_id_token") as mock_verify,
            patch("app.db", mock_firestore_client),
        ):

            mock_verify.return_value = mock_user_data

            response = client.post("/auth/verify", json={"idToken": "valid_token"})

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["valid"] is True
            assert data["user"]["uid"] == "user_123"

    def test_invalid_token_verification(self, client):
        """Test verification with invalid token"""
        with patch("firebase_admin.auth.verify_id_token") as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            response = client.post("/auth/verify", json={"idToken": "invalid_token"})

            assert response.status_code == 401
            data = json.loads(response.data)
            assert data["valid"] is False

    def test_missing_token_in_auth_request(self, client):
        """Test authentication request without token"""
        response = client.post("/auth/google", json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_user_profile_api_endpoint(self, authenticated_session, mock_firestore_client):
        """Test the user profile API endpoint"""
        profile_data = {
            "email": "test@example.com",
            "created_at": "2024-01-01T00:00:00Z",
        }

        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                profile_data
            )

            response = authenticated_session.get("/api/user/profile")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["email"] == "test@example.com"

    def test_unauthenticated_profile_access(self, client):
        """Test that unauthenticated users cannot access profile"""
        response = client.get("/api/user/profile")
        assert response.status_code in [401, 302]

    def test_session_persistence_across_requests(self, client, mock_firestore_client):
        """Test that session persists across multiple requests"""
        mock_user_data = {"uid": "user_123", "email": "test@example.com"}

        with (
            patch("firebase_admin.auth.verify_id_token") as mock_verify,
            patch("app.db", mock_firestore_client),
        ):

            mock_verify.return_value = mock_user_data
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                False
            )
            mock_firestore_client.collection.return_value.document.return_value.set.return_value = (
                None
            )

            # Authenticate
            auth_response = client.post("/auth/google", json={"idToken": "valid_token"})
            assert auth_response.status_code == 200

            # Mock for dashboard
            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = []

            # Access protected route in same session
            dashboard_response = client.get("/dashboard")
            assert dashboard_response.status_code == 200
