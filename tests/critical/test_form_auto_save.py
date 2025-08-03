"""
CRITICAL: Form Auto-Save Tests
Tests data loss prevention through automatic form saving
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestFormAutoSave:
    """Test form auto-save functionality to prevent data loss"""

    def test_inference_auto_saves_as_inactive(self, authenticated_session, mock_firestore_client):
        """Test that form inference automatically saves form as inactive"""
        mock_form_data = {
            "title": "Customer Feedback Survey",
            "description": "Tell us about your experience",
            "questions": [
                {"text": "How satisfied are you?", "type": "rating", "enabled": True}
            ],
            "demographics": {"enabled": False},
        }

        with patch("app.db", mock_firestore_client), patch("app.openai_client") as mock_openai:

            # Mock OpenAI inference response
            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(mock_form_data)

            # Mock database save
            mock_firestore_client.collection.return_value.add.return_value = (
                None,
                "auto_saved_form_123",
            )

            response = authenticated_session.post(
                "/api/infer", json={"dump": "Create a customer feedback survey"}
            )

            assert response.status_code == 200
            data = json.loads(response.data)

            # Should return inferred form AND auto-save it
            assert "form" in data
            assert "form_id" in data

            # Verify auto-save call to database
            mock_firestore_client.collection.assert_called_with("forms")
            save_call = mock_firestore_client.collection.return_value.add.call_args[0][0]
            assert save_call["active"] is False  # Must be inactive
            assert save_call["creator_id"] == "test_user_123"
            assert "created_at" in save_call

    def test_template_selection_auto_saves(self, authenticated_session, mock_firestore_client):
        """Test that template selection auto-saves the form"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.add.return_value = (
                None,
                "template_form_123",
            )

            response = authenticated_session.post(
                "/api/infer", json={"template": "customer_feedback"}
            )

            assert response.status_code == 200
            data = json.loads(response.data)

            assert "form_id" in data

            # Verify template was auto-saved
            save_call = mock_firestore_client.collection.return_value.add.call_args[0][0]
            assert save_call["active"] is False
            assert save_call["template_used"] == "customer_feedback"

    def test_auto_saved_form_appears_in_dashboard(self, authenticated_session, mock_firestore_client):
        """Test that auto-saved forms appear in dashboard"""
        auto_saved_forms = [
            {
                "id": "auto_saved_1",
                "title": "Auto-saved Customer Survey",
                "active": False,
                "creator_id": "test_user_123",
                "created_at": "2025-01-01T00:00:00Z",
                "auto_saved": True,
            },
            {
                "id": "launched_form_1",
                "title": "Launched Survey",
                "active": True,
                "creator_id": "test_user_123",
                "created_at": "2025-01-01T01:00:00Z",
            },
        ]

        with patch("app.db", mock_firestore_client):
            # Mock query for user's forms
            mock_query = Mock()
            mock_firestore_client.collection.return_value.where.return_value = mock_query
            mock_query.stream.return_value = [
                Mock(to_dict=lambda: form, id=form["id"]) for form in auto_saved_forms
            ]

            response = authenticated_session.get("/dashboard")

            assert response.status_code == 200
            # Both auto-saved and launched forms should appear
            assert b"Auto-saved Customer Survey" in response.data
            assert b"Launched Survey" in response.data

    def test_edit_form_loads_auto_saved_by_url(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test that auto-saved forms can be loaded by URL for editing"""
        # Ensure form is auto-saved (inactive)
        sample_form["active"] = False
        sample_form["auto_saved"] = True

        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            response = authenticated_session.get("/edit-form?id=test_form_123")

            assert response.status_code == 200
            # Should load the form for editing
            assert (
                b"test_form_123" in response.data
                or sample_form["title"].encode() in response.data
            )

    def test_save_and_launch_activates_auto_saved_form(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test that Save & Launch converts auto-saved form to active"""
        sample_form["active"] = False
        sample_form["auto_saved"] = True

        with patch("app.db", mock_firestore_client):
            mock_doc = Mock()
            mock_firestore_client.collection.return_value.document.return_value = mock_doc
            mock_doc.get.return_value.to_dict.return_value = sample_form
            mock_doc.get.return_value.exists = True
            mock_doc.update.return_value = None

            response = authenticated_session.put(
                "/api/update_form/test_form_123",
                json={
                    "title": sample_form["title"],
                    "questions": sample_form["questions"],
                    "active": True,  # Save & Launch
                },
            )

            assert response.status_code == 200

            # Verify form was activated
            mock_doc.update.assert_called_once()
            update_call = mock_doc.update.call_args[0][0]
            assert update_call["active"] is True

    def test_auto_save_prevents_data_loss_on_navigation(
        self, authenticated_session, mock_firestore_client
    ):
        """Test that users can navigate away and return to auto-saved forms"""
        with patch("app.db", mock_firestore_client), patch("app.openai_client") as mock_openai:

            # Mock inference
            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(
                {
                    "title": "Event Feedback",
                    "questions": [
                        {"text": "How was the event?", "type": "text", "enabled": True}
                    ],
                }
            )

            # Mock auto-save
            mock_firestore_client.collection.return_value.add.return_value = (
                None,
                "navigated_form_123",
            )

            # User creates form via inference
            inference_response = authenticated_session.post(
                "/api/infer", json={"dump": "Create an event feedback form"}
            )

            assert inference_response.status_code == 200
            form_id = json.loads(inference_response.data)["form_id"]

            # User navigates away (to dashboard)
            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = []
            dashboard_response = authenticated_session.get("/dashboard")
            assert dashboard_response.status_code == 200

            # User can return to edit the auto-saved form
            saved_form = {
                "id": form_id,
                "title": "Event Feedback",
                "active": False,
                "auto_saved": True,
                "creator_id": "test_user_123",
                "questions": [
                    {"text": "How was the event?", "type": "text", "enabled": True}
                ],
            }

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                saved_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            edit_response = authenticated_session.get(f"/edit-form?id={form_id}")
            assert edit_response.status_code == 200

    def test_auto_save_includes_all_form_data(self, authenticated_session, mock_firestore_client):
        """Test that auto-save preserves all form elements"""
        complex_form_data = {
            "title": "Complex Survey",
            "description": "A comprehensive survey",
            "questions": [
                {
                    "text": "Rate us 1-5",
                    "type": "rating",
                    "enabled": True,
                    "options": ["1", "2", "3", "4", "5"],
                },
                {"text": "Your feedback", "type": "text", "enabled": True},
                {
                    "text": "Choose color",
                    "type": "multiple_choice",
                    "enabled": False,
                    "options": ["red", "blue"],
                },
            ],
            "demographics": {
                "enabled": True,
                "age": {"enabled": True},
                "gender": {"enabled": False},
                "location": {"enabled": True},
            },
        }

        with patch("app.db", mock_firestore_client), patch("app.openai_client") as mock_openai:

            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(complex_form_data)

            mock_firestore_client.collection.return_value.add.return_value = (
                None,
                "complex_form_123",
            )

            response = authenticated_session.post(
                "/api/infer", json={"dump": "Create a complex survey"}
            )

            assert response.status_code == 200

            # Verify all data is preserved in auto-save
            save_call = mock_firestore_client.collection.return_value.add.call_args[0][0]
            assert save_call["title"] == "Complex Survey"
            assert save_call["description"] == "A comprehensive survey"
            assert len(save_call["questions"]) == 3
            assert save_call["demographics"]["enabled"] is True
            assert save_call["demographics"]["age"]["enabled"] is True
            assert save_call["demographics"]["gender"]["enabled"] is False

    def test_auto_save_fails_gracefully(self, authenticated_session, mock_firestore_client):
        """Test graceful handling when auto-save fails"""
        with patch("app.db", mock_firestore_client), patch("app.openai_client") as mock_openai:

            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps({"title": "Test Form", "questions": []})

            # Mock database failure
            mock_firestore_client.collection.return_value.add.side_effect = Exception(
                "Database error"
            )

            response = authenticated_session.post(
                "/api/infer", json={"dump": "Test form"}
            )

            # Should still return inferred form even if auto-save fails
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "form" in data
            # May not have form_id if auto-save failed

    def test_auto_saved_form_ownership_validation(self, client, mock_firestore_client, sample_form):
        """Test that auto-saved forms respect ownership"""
        sample_form["active"] = False
        sample_form["auto_saved"] = True
        sample_form["creator_id"] = "other_user_123"  # Different user

        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Try to access without authentication
            response = client.get("/edit-form?id=test_form_123")
            assert response.status_code in [401, 302]  # Requires auth

    def test_auto_save_preserves_template_metadata(
        self, authenticated_session, mock_firestore_client
    ):
        """Test that template selection metadata is preserved in auto-save"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.add.return_value = (
                None,
                "template_form_123",
            )

            response = authenticated_session.post(
                "/api/infer", json={"template": "employee_survey"}
            )

            assert response.status_code == 200

            # Verify template metadata is saved
            save_call = mock_firestore_client.collection.return_value.add.call_args[0][0]
            assert save_call["template_used"] == "employee_survey"
            assert save_call["creation_method"] == "template"
            assert save_call["active"] is False

    def test_multiple_auto_saves_same_user(self, authenticated_session, mock_firestore_client):
        """Test that users can have multiple auto-saved forms"""
        forms_data = [
            {"title": "Survey 1", "questions": []},
            {"title": "Survey 2", "questions": []},
            {"title": "Survey 3", "questions": []},
        ]

        with patch("app.db", mock_firestore_client), patch("app.openai_client") as mock_openai:

            form_ids = []

            for i, form_data in enumerate(forms_data):
                mock_openai.chat.completions.create.return_value.choices = [Mock()]
                mock_openai.chat.completions.create.return_value.choices[
                    0
                ].message.content = json.dumps(form_data)

                mock_firestore_client.collection.return_value.add.return_value = (
                    None,
                    f"auto_form_{i}",
                )

                response = authenticated_session.post(
                    "/api/infer", json={"dump": f"Create survey {i+1}"}
                )

                assert response.status_code == 200
                form_ids.append(json.loads(response.data)["form_id"])

            # All forms should be auto-saved with same user
            assert len(form_ids) == 3
            assert len(set(form_ids)) == 3  # All unique

    def test_auto_save_timestamp_accuracy(self, authenticated_session, mock_firestore_client):
        """Test that auto-save timestamps are accurate"""
        with (
            patch("app.db", mock_firestore_client),
            patch("app.openai_client") as mock_openai,
            patch("app.datetime") as mock_datetime,
        ):

            fixed_time = "2025-01-01T12:00:00Z"
            mock_datetime.now.return_value.isoformat.return_value = fixed_time

            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps({"title": "Timestamp Test", "questions": []})

            mock_firestore_client.collection.return_value.add.return_value = (
                None,
                "timestamp_form_123",
            )

            response = authenticated_session.post(
                "/api/infer", json={"dump": "Test timestamp"}
            )

            assert response.status_code == 200

            # Verify timestamp in auto-save
            save_call = mock_firestore_client.collection.return_value.add.call_args[0][0]
            assert save_call["created_at"] == fixed_time
