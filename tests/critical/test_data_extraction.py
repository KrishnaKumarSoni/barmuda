"""
CRITICAL: Data Extraction Accuracy Tests
Tests data integrity through accurate extraction from chat transcripts
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestDataExtractionAccuracy:
    """Test accurate data extraction from chat conversations"""

    def test_complete_conversation_extraction(
        self, client, mock_db, sample_chat_session
    ):
        """Test extraction of complete conversation data"""
        complete_transcript = [
            {"role": "assistant", "content": "How satisfied are you with our service?"},
            {"role": "user", "content": "I'm very satisfied, I'd say 4 out of 5"},
            {"role": "assistant", "content": "What could we improve?"},
            {"role": "user", "content": "Maybe faster response times"},
            {"role": "assistant", "content": "Thanks! [END]"},
        ]

        expected_extraction = {
            "0": {"answer": "4", "question": "How satisfied are you with our service?"},
            "1": {
                "answer": "Maybe faster response times",
                "question": "What could we improve?",
            },
        }

        with patch("app.db", mock_db), patch(
            "data_extraction.extract_responses"
        ) as mock_extract:

            mock_extract.return_value = expected_extraction

            # Mock session with transcript
            session_data = sample_chat_session.copy()
            session_data["transcript"] = complete_transcript
            session_data["status"] = "ended"

            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                session_data
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Trigger extraction (would normally happen on [END])
            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "[END]"},
            )

            # Verify extraction was called
            mock_extract.assert_called_once()

            # Verify correct data structure
            call_args = mock_extract.call_args[0]
            assert len(call_args[0]) == 5  # transcript length
            assert (
                call_args[0][1]["content"] == "I'm very satisfied, I'd say 4 out of 5"
            )

    def test_partial_conversation_extraction(
        self, client, mock_db, sample_chat_session
    ):
        """Test extraction of partial conversation (every 5 messages)"""
        partial_transcript = [
            {"role": "assistant", "content": "How satisfied are you?"},
            {"role": "user", "content": "Pretty good, 4/5"},
            {"role": "assistant", "content": "What's your age?"},
            {"role": "user", "content": "I'm 28"},
            {"role": "assistant", "content": "Where are you from?"},
        ]

        with patch("app.db", mock_db), patch(
            "data_extraction.extract_responses"
        ) as mock_extract:

            mock_extract.return_value = {
                "0": {
                    "answer": "4",
                    "question": "How satisfied are you?",
                    "partial": True,
                },
                "1": {"answer": "28", "question": "What's your age?", "partial": True},
            }

            session_data = sample_chat_session.copy()
            session_data["transcript"] = partial_transcript
            session_data["message_count"] = 5

            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                session_data
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # 5th message should trigger partial extraction
            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "San Francisco"},
            )

            # Should trigger partial save
            assert response.status_code == 200

    def test_conflicting_answers_latest_wins(self, mock_db):
        """Test that conflicting answers prioritize the latest response"""
        conflicting_transcript = [
            {"role": "assistant", "content": "Do you like coffee?"},
            {"role": "user", "content": "Yes, I love coffee"},
            {"role": "assistant", "content": "Great!"},
            {"role": "user", "content": "Actually, no I don't like it"},
            {"role": "assistant", "content": "Updating that to no—got it!"},
        ]

        with patch("data_extraction.openai_client") as mock_openai:
            # Mock OpenAI response for extraction
            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(
                {
                    "responses": {
                        "0": {
                            "answer": "no",
                            "question": "Do you like coffee?",
                            "conflicts": ["yes", "no"],
                            "resolution": "latest",
                        }
                    }
                }
            )

            from data_extraction import extract_responses

            form_data = {
                "questions": [{"text": "Do you like coffee?", "type": "yes_no"}]
            }

            result = extract_responses(conflicting_transcript, form_data)

            assert result["0"]["answer"] == "no"
            assert "conflicts" in result["0"]

    def test_skip_tagging_preservation(self, mock_db):
        """Test that [SKIP] tags are preserved in extraction"""
        skip_transcript = [
            {"role": "assistant", "content": "What's your age?"},
            {"role": "user", "content": "I'd rather not say"},
            {"role": "assistant", "content": "Totally cool! Skipping. [SKIP]"},
            {"role": "assistant", "content": "What's your favorite color?"},
            {"role": "user", "content": "Blue"},
        ]

        with patch("data_extraction.openai_client") as mock_openai:
            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(
                {
                    "responses": {
                        "0": {
                            "answer": "[SKIP]",
                            "question": "What's your age?",
                            "skipped": True,
                        },
                        "1": {
                            "answer": "Blue",
                            "question": "What's your favorite color?",
                        },
                    }
                }
            )

            from data_extraction import extract_responses

            form_data = {
                "questions": [
                    {"text": "What's your age?", "type": "number"},
                    {"text": "What's your favorite color?", "type": "text"},
                ]
            }

            result = extract_responses(skip_transcript, form_data)

            assert result["0"]["answer"] == "[SKIP]"
            assert result["0"]["skipped"] is True
            assert result["1"]["answer"] == "Blue"

    def test_no_fit_response_bucketing(self, mock_db):
        """Test that no-fit responses are bucketed to 'other'"""
        no_fit_transcript = [
            {
                "role": "assistant",
                "content": "What's your favorite color? (red, blue, green)",
            },
            {"role": "user", "content": "Yellow"},
            {"role": "assistant", "content": "Yellow's sunny! 🌞"},
        ]

        with patch("data_extraction.openai_client") as mock_openai:
            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(
                {
                    "responses": {
                        "0": {
                            "answer": "other",
                            "question": "What's your favorite color?",
                            "original_answer": "Yellow",
                            "bucketed": True,
                            "available_options": ["red", "blue", "green"],
                        }
                    }
                }
            )

            from data_extraction import extract_responses

            form_data = {
                "questions": [
                    {
                        "text": "What's your favorite color?",
                        "type": "multiple_choice",
                        "options": ["red", "blue", "green"],
                    }
                ]
            }

            result = extract_responses(no_fit_transcript, form_data)

            assert result["0"]["answer"] == "other"
            assert result["0"]["original_answer"] == "Yellow"
            assert result["0"]["bucketed"] is True

    def test_vague_response_mapping(self, mock_db):
        """Test that vague responses are mapped to closest values"""
        vague_transcript = [
            {"role": "assistant", "content": "Rate your satisfaction 1-5?"},
            {"role": "user", "content": "Meh"},
            {"role": "assistant", "content": "Meh—like a 2 or 3? 😅"},
            {"role": "user", "content": "Yeah, like a 2"},
        ]

        with patch("data_extraction.openai_client") as mock_openai:
            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(
                {
                    "responses": {
                        "0": {
                            "answer": "2",
                            "question": "Rate your satisfaction 1-5?",
                            "original_answer": "Meh",
                            "clarified": True,
                            "mapping_reasoning": "User clarified 'meh' as '2' after follow-up",
                        }
                    }
                }
            )

            from data_extraction import extract_responses

            form_data = {
                "questions": [
                    {
                        "text": "Rate your satisfaction 1-5?",
                        "type": "rating",
                        "options": ["1", "2", "3", "4", "5"],
                    }
                ]
            }

            result = extract_responses(vague_transcript, form_data)

            assert result["0"]["answer"] == "2"
            assert result["0"]["original_answer"] == "Meh"
            assert result["0"]["clarified"] is True

    def test_multi_answer_parsing_accuracy(self, mock_db):
        """Test accurate parsing of multiple answers in one response"""
        multi_answer_transcript = [
            {"role": "assistant", "content": "What's your name?"},
            {"role": "user", "content": "Alex, 25, from LA"},
            {
                "role": "assistant",
                "content": "Noted your name, Alex! I'll use the age and location later.",
            },
        ]

        with patch("data_extraction.openai_client") as mock_openai:
            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(
                {
                    "responses": {
                        "0": {"answer": "Alex", "question": "What's your name?"}
                    },
                    "pre_answered": {"age": "25", "location": "LA"},
                }
            )

            from data_extraction import extract_responses

            form_data = {
                "questions": [
                    {"text": "What's your name?", "type": "text"},
                    {"text": "What's your age?", "type": "number"},
                    {"text": "Where are you from?", "type": "text"},
                ]
            }

            result = extract_responses(multi_answer_transcript, form_data)

            assert result["0"]["answer"] == "Alex"
            assert "pre_answered" in result
            assert result["pre_answered"]["age"] == "25"
            assert result["pre_answered"]["location"] == "LA"

    def test_extraction_error_handling(self, mock_db):
        """Test handling of extraction errors and retries"""
        with patch("data_extraction.openai_client") as mock_openai:
            # First call fails
            mock_openai.chat.completions.create.side_effect = [
                Exception("API Error"),
                Mock(
                    choices=[Mock(message=Mock(content=json.dumps({"responses": {}})))]
                ),
            ]

            from data_extraction import extract_responses

            form_data = {"questions": [{"text": "Test?", "type": "text"}]}
            transcript = [{"role": "user", "content": "test"}]

            # Should retry and succeed
            result = extract_responses(transcript, form_data)

            assert isinstance(result, dict)
            assert mock_openai.chat.completions.create.call_count == 2

    def test_invalid_json_extraction_retry(self, mock_db):
        """Test retry mechanism for invalid JSON responses"""
        with patch("data_extraction.openai_client") as mock_openai:
            # First call returns invalid JSON
            mock_openai.chat.completions.create.side_effect = [
                Mock(choices=[Mock(message=Mock(content="Invalid JSON {"))]),
                Mock(
                    choices=[Mock(message=Mock(content=json.dumps({"responses": {}})))]
                ),
            ]

            from data_extraction import extract_responses

            form_data = {"questions": []}
            transcript = []

            result = extract_responses(transcript, form_data)

            assert isinstance(result, dict)
            assert mock_openai.chat.completions.create.call_count == 2

    def test_demographics_data_extraction(self, mock_db):
        """Test extraction of demographics data"""
        demographics_transcript = [
            {"role": "assistant", "content": "What's your age range?"},
            {"role": "user", "content": "I'm 28"},
            {"role": "assistant", "content": "How do you identify gender-wise?"},
            {"role": "user", "content": "Male"},
        ]

        with patch("data_extraction.openai_client") as mock_openai:
            mock_openai.chat.completions.create.return_value.choices = [Mock()]
            mock_openai.chat.completions.create.return_value.choices[
                0
            ].message.content = json.dumps(
                {"responses": {}, "demographics": {"age": "25-30", "gender": "Male"}}
            )

            from data_extraction import extract_responses

            form_data = {
                "questions": [],
                "demographics": {
                    "enabled": True,
                    "age": {"enabled": True},
                    "gender": {"enabled": True},
                },
            }

            result = extract_responses(demographics_transcript, form_data)

            assert "demographics" in result
            assert result["demographics"]["age"] == "25-30"
            assert result["demographics"]["gender"] == "Male"

    def test_extraction_metadata_accuracy(self, client, mock_db, sample_chat_session):
        """Test that extraction preserves important metadata"""
        with patch("app.db", mock_db), patch(
            "data_extraction.extract_responses"
        ) as mock_extract:

            mock_extract.return_value = {
                "responses": {"0": {"answer": "test"}},
                "metadata": {
                    "extracted_at": "2025-01-01T00:00:00Z",
                    "partial": False,
                    "total_messages": 10,
                    "extraction_method": "complete",
                },
            }

            session_data = sample_chat_session.copy()
            session_data["status"] = "ended"

            mock_db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                session_data
            )
            mock_db.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Mock saving extracted data
            mock_db.collection.return_value.add.return_value = (None, "response_123")

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "[END]"},
            )

            # Verify metadata is preserved
            assert response.status_code == 200
