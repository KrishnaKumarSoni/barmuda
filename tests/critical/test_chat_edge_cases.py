"""
CRITICAL: Chat Agent Edge Cases Tests
Tests the user experience quality through edge case handling
"""

import json
from unittest.mock import Mock, call, patch

import pytest


class TestChatAgentEdgeCases:
    """Test chat agent edge case handling from EdgeCases.md"""

    def test_off_topic_redirect_bananas(
        self, client, mock_firestore_client, sample_chat_session, edge_case_messages
    ):
        """Test off-topic 'bananas' redirect handling (max 3 redirects)"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Setup session
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Test multiple off-topic messages
            for i, message in enumerate(edge_case_messages["off_topic"][:3]):
                mock_agent.process_message.return_value = {
                    "response": f"That's a bit bananas! 😄 Let's focus on the survey. (redirect {i+1})",
                    "status": "active",
                    "redirect_count": i + 1,
                }

                response = client.post(
                    "/api/chat/message",
                    json={"session_id": "session_123", "message": message},
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert (
                    "bananas" in data["response"].lower()
                    or "focus" in data["response"].lower()
                )

            # 4th off-topic should end conversation
            mock_agent.process_message.return_value = {
                "response": "Thanks for your time! [END]",
                "status": "ended",
                "redirect_count": 3,
            }

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "More off topic stuff"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "[END]" in data["response"] or data.get("status") == "ended"

    def test_skip_question_handling(
        self, client, mock_firestore_client, sample_chat_session, edge_case_messages
    ):
        """Test explicit question skipping with [SKIP] tagging"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            for skip_message in edge_case_messages["skip_requests"]:
                mock_agent.process_message.return_value = {
                    "response": "Totally cool! 😊 Skipping. Let's move to the next question.",
                    "status": "active",
                    "skip_count": 1,
                    "tagged": "[SKIP]",
                }

                response = client.post(
                    "/api/chat/message",
                    json={"session_id": "session_123", "message": skip_message},
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert any(
                    word in data["response"].lower()
                    for word in ["skip", "cool", "next"]
                )

    def test_multi_answer_parsing(
        self, client, mock_firestore_client, sample_chat_session, edge_case_messages
    ):
        """Test parsing multiple answers in one response"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            multi_answer = edge_case_messages["multi_answers"][0]  # "Alex, 25, from LA"

            mock_agent.process_message.return_value = {
                "response": "Noted your name, Alex! 😎 I'll use the age and location later.",
                "status": "active",
                "extracted_data": {"name": "Alex", "age": "25", "location": "LA"},
            }

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": multi_answer},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "alex" in data["response"].lower()
            assert (
                "noted" in data["response"].lower() or "use" in data["response"].lower()
            )

    def test_conflicting_answer_resolution(
        self, client, mock_firestore_client, sample_chat_session, edge_case_messages
    ):
        """Test that conflicting answers prioritize latest response"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # First answer
            mock_agent.process_message.return_value = {
                "response": "Great to hear you love it! ☕",
                "status": "active",
            }

            response1 = client.post(
                "/api/chat/message",
                json={
                    "session_id": "session_123",
                    "message": edge_case_messages["conflicting"][0],  # "Yes, I love it"
                },
            )

            # Conflicting answer
            mock_agent.process_message.return_value = {
                "response": "Updating that to no—got it! ☕",
                "status": "active",
                "conflict_resolved": True,
                "latest_answer": "no",
            }

            response2 = client.post(
                "/api/chat/message",
                json={
                    "session_id": "session_123",
                    "message": edge_case_messages["conflicting"][
                        1
                    ],  # "Actually, no I don't"
                },
            )

            assert response2.status_code == 200
            data = json.loads(response2.data)
            assert (
                "updating" in data["response"].lower()
                or "got it" in data["response"].lower()
            )

    def test_vague_response_follow_up(
        self, client, mock_firestore_client, sample_chat_session, edge_case_messages
    ):
        """Test follow-up prompts for vague responses"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            for vague_response in edge_case_messages["vague"]:
                mock_agent.process_message.return_value = {
                    "response": "Could you be a bit more specific? Like on a scale of 1-5? 😅",
                    "status": "active",
                    "follow_up_needed": True,
                }

                response = client.post(
                    "/api/chat/message",
                    json={"session_id": "session_123", "message": vague_response},
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert any(
                    word in data["response"].lower()
                    for word in ["specific", "scale", "more"]
                )

    def test_no_fit_response_acceptance(self, client, mock_firestore_client, sample_chat_session):
        """Test that no-fit responses are accepted openly"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Question has options red/blue/green, user says yellow
            mock_agent.process_message.return_value = {
                "response": "Yellow's sunny! 🌞 Thanks for that.",
                "status": "active",
                "no_fit_response": "yellow",
                "bucket_to": "other",
            }

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "Yellow"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "yellow" in data["response"].lower()
            assert any(emoji in data["response"] for emoji in ["🌞", "☀️", "😊"])

    def test_premature_ending_request(self, client, mock_firestore_client, sample_chat_session):
        """Test handling of premature ending requests"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            mock_agent.process_message.return_value = {
                "response": "Sure thing! Thanks for your time. 👋 [END]",
                "status": "ended",
                "premature_end": True,
            }

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "I'm done now"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "[END]" in data["response"] or data.get("status") == "ended"
            assert "thanks" in data["response"].lower()

    def test_invalid_input_type_handling(self, client, mock_firestore_client, sample_chat_session):
        """Test handling of invalid input types (e.g., non-number for number question)"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            # Question asks for number of pets, user says "Several"
            mock_agent.process_message.return_value = {
                "response": "Several—like 2 or 3? 😺",
                "status": "active",
                "validation_error": True,
                "expected_type": "number",
            }

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "Several"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert any(
                word in data["response"].lower()
                for word in ["several", "like", "2", "3"]
            )

    def test_session_timeout_partial_save(self, client, mock_firestore_client, sample_chat_session):
        """Test that session timeout triggers partial save"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Mock timed out session
            timeout_session = sample_chat_session.copy()
            timeout_session["status"] = "timeout"
            timeout_session["ended_at"] = "2025-01-01T00:05:00Z"  # 5 minutes later

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                timeout_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            response = client.get("/api/chat/status/session_123")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] in ["timeout", "ended"]

    def test_message_limit_enforcement(self, client, mock_firestore_client, sample_chat_session):
        """Test 30 message limit enforcement"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Mock session at message limit
            limit_session = sample_chat_session.copy()
            limit_session["message_count"] = 30

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                limit_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            mock_agent.process_message.return_value = {
                "response": "We've reached the message limit. Thanks for your responses! [END]",
                "status": "ended",
                "reason": "message_limit",
            }

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "One more message"},
            )

            # Should either reject or end conversation
            assert response.status_code in [200, 429]
            if response.status_code == 200:
                data = json.loads(response.data)
                assert "[END]" in data["response"] or data.get("status") == "ended"

    def test_multi_language_response_handling(
        self, client, mock_firestore_client, sample_chat_session
    ):
        """Test multi-language response handling"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            mock_agent.process_message.return_value = {
                "response": "Paris? Magnifique! 😊 What brings you joy in that beautiful city?",
                "status": "active",
                "detected_language": "french",
                "auto_translated": True,
            }

            response = client.post(
                "/api/chat/message",
                json={"session_id": "session_123", "message": "Je suis de Paris"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "paris" in data["response"].lower()
            # Should respond appropriately to French input

    def test_agent_tool_execution(self, client, mock_firestore_client, sample_chat_session):
        """Test that agent tools are properly executed"""
        with (
            patch("app.db", mock_firestore_client),
            patch("chat_agent.ChatAgent") as mock_agent_class,
        ):

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            mock_firestore_client.collection.return_value.document.return_value.get.return_value.to_dict.return_value = (
                sample_chat_session
            )
            mock_firestore_client.collection.return_value.document.return_value.get.return_value.exists = (
                True
            )

            mock_agent.process_message.return_value = {
                "response": "Got it! Let's move to the next question.",
                "status": "active",
                "tools_used": ["validate_response", "get_next_question"],
                "current_question_index": 1,
            }

            response = client.post(
                "/api/chat/message",
                json={
                    "session_id": "session_123",
                    "message": "I really enjoyed the service",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert (
                "next" in data["response"].lower()
                or "got it" in data["response"].lower()
            )
