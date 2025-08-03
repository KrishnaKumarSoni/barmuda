"""
IMPORTANT: Export Functionality Accuracy Tests
Tests CSV/JSON export accuracy and data integrity
"""

import csv
import io
import json
from unittest.mock import Mock, patch

import pytest


class TestExportAccuracy:
    """Test export functionality for CSV and JSON formats"""

    def test_csv_export_basic_structure(
        self, authenticated_session, mock_firestore_client, sample_form, sample_responses
    ):
        """Test basic CSV export structure and headers"""
        with patch("app.db", mock_firestore_client):
            # Mock form lookup
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock responses query
            mock_responses_data = [
                {
                    "session_id": "session_1",
                    "responses": {"0": "5", "1": "Great service!"},
                    "metadata": {
                        "completed_at": "2025-01-01T00:00:00Z",
                        "partial": False,
                    },
                },
                {
                    "session_id": "session_2",
                    "responses": {"0": "3", "1": "Could be better"},
                    "metadata": {
                        "completed_at": "2025-01-01T01:00:00Z",
                        "partial": False,
                    },
                },
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in mock_responses_data
            ]

            response = authenticated_session.get("/api/export/test_form_123/csv")

            assert response.status_code == 200
            assert response.content_type == "text/csv"

            # Parse CSV content
            csv_content = response.data.decode("utf-8")
            csv_reader = csv.reader(io.StringIO(csv_content))
            rows = list(csv_reader)

            # Should have header row + data rows
            assert len(rows) >= 3  # Header + 2 data rows

            # Check headers
            headers = rows[0]
            assert "session_id" in headers
            assert "completed_at" in headers
            assert any("How satisfied" in header for header in headers)  # Question text

    def test_csv_export_data_accuracy(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test CSV export data accuracy and formatting"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock specific response data
            test_responses = [
                {
                    "session_id": "precise_test_1",
                    "responses": {
                        "0": "4",  # Rating question
                        "1": "More features, please!",  # Text with comma and punctuation
                    },
                    "metadata": {
                        "completed_at": "2025-01-01T12:30:45Z",
                        "partial": False,
                        "device_id": "device_123",
                    },
                    "demographics": {"age": "25-30", "gender": "Male"},
                }
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in test_responses
            ]

            response = authenticated_session.get("/api/export/test_form_123/csv")

            assert response.status_code == 200

            csv_content = response.data.decode("utf-8")
            csv_reader = csv.reader(io.StringIO(csv_content))
            rows = list(csv_reader)

            # Find data row
            data_row = rows[1]  # First data row after header

            # Verify session_id is preserved
            session_id_index = rows[0].index("session_id")
            assert data_row[session_id_index] == "precise_test_1"

            # Verify response data is properly quoted and formatted
            assert "4" in data_row  # Rating response
            assert (
                "More features, please!" in data_row
            )  # Text response with punctuation

    def test_csv_export_handles_special_characters(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test CSV export properly handles special characters and escaping"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock responses with special characters
            special_responses = [
                {
                    "session_id": "special_chars_test",
                    "responses": {
                        "0": "5",
                        "1": 'Text with "quotes", commas, and\nnewlines',
                    },
                    "metadata": {
                        "completed_at": "2025-01-01T00:00:00Z",
                        "partial": False,
                    },
                }
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in special_responses
            ]

            response = authenticated_session.get("/api/export/test_form_123/csv")

            assert response.status_code == 200

            # CSV should properly escape special characters
            csv_content = response.data.decode("utf-8")
            assert (
                'Text with "quotes"' in csv_content
                or '"Text with ""quotes""' in csv_content
            )

    def test_json_export_structure(self, authenticated_session, mock_firestore_client, sample_form):
        """Test JSON export structure and completeness"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            mock_responses = [
                {
                    "session_id": "json_test_1",
                    "responses": {"0": "4", "1": "Good service"},
                    "metadata": {
                        "completed_at": "2025-01-01T00:00:00Z",
                        "partial": False,
                        "device_id": "device_456",
                    },
                    "demographics": {"age": "30-35"},
                }
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in mock_responses
            ]

            response = authenticated_session.get("/api/export/test_form_123/json")

            assert response.status_code == 200
            assert response.content_type == "application/json"

            # Parse JSON
            json_data = json.loads(response.data)

            # Should have form metadata and responses
            assert "form" in json_data
            assert "responses" in json_data
            assert "export_metadata" in json_data

            # Form metadata
            assert json_data["form"]["title"] == sample_form["title"]
            assert json_data["form"]["id"] == "test_form_123"

            # Response data
            assert len(json_data["responses"]) == 1
            assert json_data["responses"][0]["session_id"] == "json_test_1"

    def test_json_export_data_types_preserved(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test that JSON export preserves data types correctly"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock responses with various data types
            typed_responses = [
                {
                    "session_id": "types_test",
                    "responses": {"0": 4, "1": "Text response"},  # Number  # String
                    "metadata": {
                        "completed_at": "2025-01-01T00:00:00Z",
                        "partial": False,
                        "device_id": "device_789",
                        "message_count": 10,  # Number
                    },
                    "demographics": {"age": "25-30", "enabled": True},  # Boolean
                }
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in typed_responses
            ]

            response = authenticated_session.get("/api/export/test_form_123/json")

            assert response.status_code == 200

            json_data = json.loads(response.data)
            response_data = json_data["responses"][0]

            # Verify data types are preserved
            assert isinstance(response_data["responses"]["0"], int)
            assert isinstance(response_data["responses"]["1"], str)
            assert isinstance(response_data["metadata"]["message_count"], int)
            assert isinstance(response_data["demographics"]["enabled"], bool)

    def test_export_empty_responses(self, authenticated_session, mock_firestore_client, sample_form):
        """Test export behavior with no responses"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock empty responses
            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = []

            # Test CSV export
            csv_response = authenticated_session.get("/api/export/test_form_123/csv")
            assert csv_response.status_code == 200

            csv_content = csv_response.data.decode("utf-8")
            csv_rows = list(csv.reader(io.StringIO(csv_content)))
            assert len(csv_rows) == 1  # Only header row

            # Test JSON export
            json_response = authenticated_session.get("/api/export/test_form_123/json")
            assert json_response.status_code == 200

            json_data = json.loads(json_response.data)
            assert json_data["responses"] == []

    def test_export_partial_responses_flagged(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test that partial responses are properly flagged in exports"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mix of complete and partial responses
            mixed_responses = [
                {
                    "session_id": "complete_1",
                    "responses": {"0": "5", "1": "Complete response"},
                    "metadata": {
                        "completed_at": "2025-01-01T00:00:00Z",
                        "partial": False,
                    },
                },
                {
                    "session_id": "partial_1",
                    "responses": {"0": "3"},  # Missing response to question 1
                    "metadata": {
                        "completed_at": "2025-01-01T00:30:00Z",
                        "partial": True,
                    },
                },
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in mixed_responses
            ]

            # Test CSV export
            csv_response = authenticated_session.get("/api/export/test_form_123/csv")
            assert csv_response.status_code == 200

            csv_content = csv_response.data.decode("utf-8")
            assert "partial" in csv_content.lower()

            # Test JSON export
            json_response = authenticated_session.get("/api/export/test_form_123/json")
            assert json_response.status_code == 200

            json_data = json.loads(json_response.data)

            # Find partial response
            partial_response = next(
                r for r in json_data["responses"] if r["session_id"] == "partial_1"
            )
            assert partial_response["metadata"]["partial"] is True

    def test_export_demographics_inclusion(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test that demographics data is included in exports"""
        with patch("app.db", mock_firestore_client):
            # Enable demographics in form
            form_with_demographics = sample_form.copy()
            form_with_demographics["demographics"] = {
                "enabled": True,
                "age": {"enabled": True},
                "gender": {"enabled": True},
            }

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                form_with_demographics
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            responses_with_demographics = [
                {
                    "session_id": "demo_test",
                    "responses": {"0": "4"},
                    "demographics": {"age": "25-30", "gender": "Female"},
                    "metadata": {
                        "completed_at": "2025-01-01T00:00:00Z",
                        "partial": False,
                    },
                }
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in responses_with_demographics
            ]

            # Test CSV includes demographics columns
            csv_response = authenticated_session.get("/api/export/test_form_123/csv")
            assert csv_response.status_code == 200

            csv_content = csv_response.data.decode("utf-8")
            csv_reader = csv.reader(io.StringIO(csv_content))
            headers = next(csv_reader)

            assert "age" in headers
            assert "gender" in headers

            # Test JSON includes demographics
            json_response = authenticated_session.get("/api/export/test_form_123/json")
            json_data = json.loads(json_response.data)

            assert "demographics" in json_data["responses"][0]
            assert json_data["responses"][0]["demographics"]["age"] == "25-30"

    def test_export_metadata_accuracy(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test export metadata accuracy and timestamps"""
        with patch("app.db", mock_firestore_client), patch("app.datetime") as mock_datetime:

            fixed_export_time = "2025-01-02T10:00:00Z"
            mock_datetime.now.return_value.isoformat.return_value = fixed_export_time

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )
            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = []

            response = authenticated_session.get("/api/export/test_form_123/json")
            assert response.status_code == 200

            json_data = json.loads(response.data)
            export_meta = json_data["export_metadata"]

            assert export_meta["exported_at"] == fixed_export_time
            assert export_meta["exported_by"] == "test_user_123"
            assert export_meta["total_responses"] == 0
            assert export_meta["format"] == "json"

    def test_export_large_dataset_performance(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test export performance with large datasets"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock large dataset
            large_responses = [
                {
                    "session_id": f"session_{i}",
                    "responses": {"0": str(i % 5 + 1), "1": f"Response {i}"},
                    "metadata": {
                        "completed_at": "2025-01-01T00:00:00Z",
                        "partial": False,
                    },
                }
                for i in range(1000)
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda resp=resp: resp) for resp in large_responses
            ]

            import time

            start_time = time.time()
            response = authenticated_session.get("/api/export/test_form_123/csv")
            end_time = time.time()

            assert response.status_code == 200
            # Should complete in reasonable time (< 10 seconds for 1000 records)
            assert (end_time - start_time) < 10.0

    def test_export_duplicate_detection(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test that duplicate responses are flagged in export"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock responses with same device_id (potential duplicates)
            duplicate_responses = [
                {
                    "session_id": "session_1",
                    "responses": {"0": "5"},
                    "metadata": {
                        "completed_at": "2025-01-01T00:00:00Z",
                        "partial": False,
                        "device_id": "duplicate_device",
                    },
                },
                {
                    "session_id": "session_2",
                    "responses": {"0": "4"},
                    "metadata": {
                        "completed_at": "2025-01-01T01:00:00Z",
                        "partial": False,
                        "device_id": "duplicate_device",  # Same device
                    },
                },
            ]

            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = [
                Mock(to_dict=lambda: resp) for resp in duplicate_responses
            ]

            response = authenticated_session.get("/api/export/test_form_123/json")
            assert response.status_code == 200

            json_data = json.loads(response.data)

            # Should flag potential duplicates
            device_ids = [r["metadata"]["device_id"] for r in json_data["responses"]]
            assert len(set(device_ids)) < len(device_ids)  # Duplicates present

    def test_export_file_naming_convention(
        self, authenticated_session, mock_firestore_client, sample_form
    ):
        """Test export file naming and content-disposition headers"""
        with patch("app.db", mock_firestore_client):
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_form
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )
            mock_firestore_client.collection.return_value.where.return_value.stream.return_value = []

            csv_response = authenticated_session.get("/api/export/test_form_123/csv")
            assert csv_response.status_code == 200

            # Check content-disposition header for proper filename
            content_disposition = csv_response.headers.get("Content-Disposition", "")
            assert "attachment" in content_disposition
            assert (
                "test_form_123" in content_disposition
                or "Customer Feedback Survey" in content_disposition
            )
            assert ".csv" in content_disposition

            json_response = authenticated_session.get("/api/export/test_form_123/json")
            assert json_response.status_code == 200

            content_disposition = json_response.headers.get("Content-Disposition", "")
            assert ".json" in content_disposition
