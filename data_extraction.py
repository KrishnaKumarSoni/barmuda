"""
Barmuda Data Extraction Chain
LLM-powered extraction of structured responses from chat conversations
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import firebase_admin
import openai
from dotenv import load_dotenv
from firebase_admin import firestore

load_dotenv()

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Firebase should already be initialized by app.py
# Get the client safely
try:
    firestore_db = firestore.client()
except Exception as e:
    print(f"Warning: Could not get Firestore client immediately: {e}")
    firestore_db = None


class DataExtractionChain:
    """LLM-powered data extraction from chat conversations"""

    def __init__(self):
        self.client = openai.OpenAI()

    def extract_responses(self, session_data: Dict) -> Dict[str, Any]:
        """Extract structured responses from chat conversation"""
        try:
            # Get form structure and chat history
            form_questions = session_data.get("form_data", {}).get("questions", [])
            chat_history = session_data.get("chat_history", [])
            existing_responses = session_data.get("responses", {})

            # Build extraction prompt
            extraction_prompt = self._build_extraction_prompt(
                form_questions, chat_history, existing_responses
            )

            # Call OpenAI for extraction
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured data from conversational text.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            # Parse the extracted data
            extracted_data = json.loads(response.choices[0].message.content)

            # Post-process and validate
            processed_data = self._post_process_extraction(
                extracted_data, form_questions, existing_responses
            )

            return {
                "success": True,
                "extracted_responses": processed_data,
                "extraction_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "method": "llm_extraction",
                    "model": "gpt-4o-mini",
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_responses": existing_responses,
                "extraction_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "method": "fallback",
                    "error": str(e),
                },
            }

    def _build_extraction_prompt(
        self, questions: List[Dict], chat_history: List[Dict], existing_responses: Dict
    ) -> str:
        """Build the extraction prompt for LLM"""

        # Filter only user and assistant messages
        conversation = []
        for msg in chat_history:
            if msg.get("role") in ["user", "assistant"]:
                conversation.append(f"{msg['role'].title()}: {msg['content']}")

        conversation_text = "\n".join(conversation)

        prompt = f"""
Extract structured responses from this chat conversation. The user was answering form questions.

FORM QUESTIONS:
{json.dumps(questions, indent=2)}

EXISTING RESPONSES (already saved):
{json.dumps(existing_responses, indent=2)}

CONVERSATION:
{conversation_text}

EXTRACTION RULES:
1. Extract answers to form questions from the user's messages
2. Handle edge cases:
   - [SKIP] for explicitly skipped questions
   - Map vague responses to closest valid option
   - For multiple choice: bucket to existing options or "other"
   - For ratings: convert words to numbers (e.g., "good" → 4)
   - For yes/no: normalize variations (e.g., "yeah" → "yes")
3. Prioritize latest answers if there are conflicts
4. Only extract clear, confident matches
5. Don't overwrite existing responses unless there's a clear update

OUTPUT FORMAT (JSON):
{{
  "responses": {{
    "0": {{"value": "extracted_answer", "confidence": 0.9, "source": "user_message_excerpt"}},
    "1": {{"value": "[SKIP]", "confidence": 1.0, "source": "explicit_skip"}},
    "2": {{"value": "processed_answer", "confidence": 0.8, "source": "user_message_excerpt"}}
  }},
  "extraction_notes": "Any important notes about the extraction process"
}}
"""
        return prompt

    def _post_process_extraction(
        self, extracted_data: Dict, questions: List[Dict], existing_responses: Dict
    ) -> Dict:
        """Post-process and validate extracted responses"""
        processed_responses = existing_responses.copy()

        extracted_responses = extracted_data.get("responses", {})

        for question_idx, response_data in extracted_responses.items():
            try:
                idx = int(question_idx)
                if idx < len(questions):
                    question = questions[idx]
                    response_value = response_data.get("value")
                    confidence = response_data.get("confidence", 0.5)

                    # Only update if confidence is high enough
                    if confidence >= 0.7:
                        # Type-specific processing
                        processed_value = self._process_by_type(
                            response_value,
                            question.get("type", "text"),
                            question.get("options", []),
                        )

                        processed_responses[question_idx] = {
                            "value": processed_value,
                            "timestamp": datetime.now().isoformat(),
                            "extraction_confidence": confidence,
                            "question_text": question.get("text", ""),
                            "source": response_data.get("source", "chat_extraction"),
                        }
            except (ValueError, KeyError):
                continue

        return processed_responses

    def _process_by_type(
        self, value: str, question_type: str, options: List[str]
    ) -> str:
        """Process response based on question type"""
        if value == "[SKIP]":
            return value

        if question_type == "yes_no":
            value_lower = str(value).lower()
            if any(
                word in value_lower
                for word in ["yes", "y", "yeah", "yep", "sure", "ok", "true", "1"]
            ):
                return "yes"
            elif any(
                word in value_lower for word in ["no", "n", "nope", "nah", "false", "0"]
            ):
                return "no"
            else:
                return "unclear"

        elif question_type == "rating":
            try:
                # Try to extract number
                import re

                numbers = re.findall(r"\d+", str(value))
                if numbers:
                    rating = int(numbers[0])
                    if 1 <= rating <= 5:
                        return str(rating)

                # Try word mapping
                rating_map = {
                    "terrible": "1",
                    "awful": "1",
                    "bad": "1",
                    "poor": "2",
                    "meh": "2",
                    "okay": "3",
                    "ok": "3",
                    "good": "4",
                    "great": "4",
                    "excellent": "5",
                    "amazing": "5",
                    "perfect": "5",
                }
                value_lower = str(value).lower()
                for word, rating in rating_map.items():
                    if word in value_lower:
                        return rating

                return "unclear"
            except:
                return "unclear"

        elif question_type == "multiple_choice" and options:
            # Try to match to existing options
            value_lower = str(value).lower()
            for option in options:
                if option.lower() in value_lower or value_lower in option.lower():
                    return option
            # If no match, return "other"
            return "other"

        else:  # text or unknown type
            return str(value)


def extract_chat_responses(session_id: str) -> Dict[str, Any]:
    """Main function to extract responses from a chat session"""
    try:
        # Get Firestore client (handle case where it wasn't available at import)
        global firestore_db
        if firestore_db is None:
            firestore_db = firestore.client()
            
        # Load session data from Firestore
        session_doc = (
            firestore_db.collection("chat_sessions").document(session_id).get()
        )

        if not session_doc.exists:
            return {"success": False, "error": "Session not found"}

        session_data = session_doc.to_dict()

        # Use extraction chain
        extractor = DataExtractionChain()
        extraction_result = extractor.extract_responses(session_data)

        if extraction_result["success"]:
            # Save extracted responses to Firestore
            response_data = {
                "session_id": session_id,
                "form_id": session_data.get("form_id"),
                "creator_id": session_data.get("form_data", {}).get("creator_id"),
                "form_title": session_data.get("form_data", {}).get(
                    "title", "Untitled Form"
                ),
                "responses": extraction_result["extracted_responses"],
                "metadata": {
                    **session_data.get("metadata", {}),
                    "chat_length": len(session_data.get("chat_history", [])),
                    **extraction_result["extraction_metadata"],
                    "device_id": session_data.get("metadata", {}).get("device_id"),
                    "location": session_data.get("metadata", {}).get("location", {}),
                },
                "created_at": datetime.now(),
                "partial": session_data.get("metadata", {}).get("partial", False),
            }

            # Save to responses collection
            doc_ref = firestore_db.collection("responses").add(response_data)

            # Update form stats
            form_id = session_data.get("form_id")
            if form_id:
                form_ref = firestore_db.collection("forms").document(form_id)
                form_ref.update(
                    {
                        "response_count": firestore.Increment(1),
                        "last_response": datetime.now(),
                    }
                )

            return {
                "success": True,
                "response_id": doc_ref[1].id,
                "extracted_responses": len(extraction_result["extracted_responses"]),
                "extraction_metadata": extraction_result["extraction_metadata"],
            }
        else:
            return extraction_result

    except Exception as e:
        return {"success": False, "error": str(e)}


# For backward compatibility
def extract_responses_from_session(session_id: str):
    """Legacy function name for compatibility"""
    return extract_chat_responses(session_id)
