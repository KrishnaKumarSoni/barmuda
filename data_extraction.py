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
        """Build the extraction prompt for LLM with generalized, robust prompting"""

        # Filter only user and assistant messages
        conversation = []
        for msg in chat_history:
            if msg.get("role") in ["user", "assistant"]:
                conversation.append(f"{msg['role'].title()}: {msg['content']}")

        conversation_text = "\n".join(conversation)

        prompt = f"""You are an expert data extraction specialist. Your task is to analyze a conversational survey and extract structured responses.

# CONTEXT
This is a chat conversation where a user answered survey questions in natural language. Extract their responses accurately and intelligently.

# SURVEY QUESTIONS
{json.dumps(questions, indent=2)}

# EXISTING RESPONSES (do not overwrite unless user clearly changed their answer)
{json.dumps(existing_responses, indent=2)}

# CONVERSATION TRANSCRIPT
{conversation_text}

# EXTRACTION GUIDELINES

## Core Principles
1. **Accuracy First**: Only extract responses you're confident about
2. **Natural Language Understanding**: Users speak naturally, not in structured formats
3. **Context Awareness**: Consider the full conversation flow and context
4. **Intent Recognition**: Understand what the user is really trying to communicate

## Response Processing Rules

### For Multiple Choice Questions
- Match user responses to available options using semantic understanding
- If no clear match exists, use "other" as the value
- Consider synonyms, abbreviations, and common variations
- Example: "LinkedIn" matches options like "LinkedIn", "Linkedin", "Social Media", etc.

### For Yes/No Questions  
- Recognize affirmative responses: yes, yeah, yep, sure, definitely, absolutely, correct, right, true, y, 1
- Recognize negative responses: no, nope, nah, negative, false, wrong, incorrect, n, 0
- If unclear, mark as "unclear" rather than guessing

### For Rating Questions (typically 1-5 scale)
- Extract numeric ratings directly: "4", "5/5", "4 out of 5"
- Convert descriptive ratings to numbers:
  - Extremely negative (terrible, awful, hate it): 1
  - Negative (bad, poor, don't like): 2  
  - Neutral (okay, fine, meh, average): 3
  - Positive (good, like it, nice): 4
  - Extremely positive (excellent, amazing, love it, perfect): 5
- If ambiguous, use "unclear"

### For Text Questions
- Extract the complete, relevant response from user messages
- Clean up obvious typos but preserve meaning and tone
- Combine multiple related messages if they form one complete answer
- Remove filler words but keep substantive content

### For Number Questions
- Extract numeric values, converting written numbers to digits
- Handle ranges by taking the midpoint or most specific value mentioned
- If user gives non-numeric answer, mark as "unclear"

## Special Cases
- **Explicit Skips**: When user explicitly says "skip", "pass", "I don't want to answer", use "[SKIP]"
- **Off-topic Responses**: If user goes completely off-topic, don't force an extraction
- **Multiple Answers**: If user changes their mind, use the most recent/final answer
- **Partial Information**: Extract what's clearly stated, don't fill in gaps

## Confidence Scoring
- 1.0: Explicit, clear answer (user directly states the response)
- 0.9: Very clear semantic match (obvious intent, slight variation in wording)
- 0.8: Good semantic match (requires some interpretation but intent is clear)
- 0.7: Moderate confidence (some ambiguity but reasonable interpretation)
- 0.6 or below: Don't extract (too ambiguous)

# OUTPUT REQUIREMENTS
Return a JSON object with this exact structure:

{{
  "responses": {{
    "question_index": {{
      "value": "extracted_response",
      "confidence": 0.0-1.0,
      "source": "relevant_user_message_excerpt",
      "reasoning": "brief_explanation_of_extraction_logic"
    }}
  }},
  "extraction_metadata": {{
    "total_questions": number,
    "responses_extracted": number,
    "high_confidence_responses": number,
    "notes": "any_important_observations"
  }}
}}

Only include responses where confidence >= 0.7. Be conservative rather than making incorrect guesses."""
        return prompt

    def _post_process_extraction(
        self, extracted_data: Dict, questions: List[Dict], existing_responses: Dict
    ) -> Dict:
        """Post-process and validate extracted responses - minimal processing since GPT handles it"""
        processed_responses = existing_responses.copy()

        extracted_responses = extracted_data.get("responses", {})

        for question_idx, response_data in extracted_responses.items():
            try:
                idx = int(question_idx)
                if idx < len(questions):
                    question = questions[idx]
                    response_value = response_data.get("value")
                    confidence = response_data.get("confidence", 0.5)
                    source = response_data.get("source", "chat_extraction")
                    reasoning = response_data.get("reasoning", "")

                    # Only update if confidence is high enough and response isn't empty
                    if confidence >= 0.7 and response_value and response_value.strip():
                        processed_responses[question_idx] = {
                            "value": response_value,
                            "timestamp": datetime.now().isoformat(),
                            "extraction_confidence": confidence,
                            "question_text": question.get("text", ""),
                            "source": source,
                            "reasoning": reasoning,
                            "extraction_method": "gpt4o_mini_direct"
                        }
            except (ValueError, KeyError) as e:
                print(f"Error processing extracted response for question {question_idx}: {e}")
                continue

        return processed_responses


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

            # Add chat transcript for debugging/review
            response_data["chat_transcript"] = session_data.get("chat_history", [])
            
            # Save to responses collection
            doc_ref = firestore_db.collection("responses").add(response_data)

            # Update form stats and check for email notifications
            form_id = session_data.get("form_id")
            if form_id:
                form_ref = firestore_db.collection("forms").document(form_id)
                
                # Get current response count to determine if we should send email
                form_doc = form_ref.get()
                current_count = 0
                creator_email = None
                creator_name = None
                form_title = session_data.get("form_data", {}).get("title", "Untitled Form")
                
                if form_doc.exists:
                    form_data = form_doc.to_dict()
                    current_count = form_data.get("response_count", 0)
                    creator_id = form_data.get("creator_id")
                    
                    # Get creator info for email
                    if creator_id:
                        try:
                            creator_doc = firestore_db.collection("users").document(creator_id).get()
                            if creator_doc.exists:
                                creator_data = creator_doc.to_dict()
                                creator_email = creator_data.get("email")
                                creator_name = creator_data.get("name")
                        except Exception as e:
                            print(f"Could not get creator info for email: {str(e)}")
                
                # Update form stats
                new_count = current_count + 1
                form_ref.update(
                    {
                        "response_count": firestore.Increment(1),
                        "last_response": datetime.now(),
                    }
                )
                
                # Send email notifications for milestone responses
                if creator_email and new_count in [1, 5, 10]:
                    try:
                        from email_service import email_service
                        email_result = email_service.send_response_alert(
                            creator_email, form_title, new_count, form_id, creator_name
                        )
                        if email_result.get("success"):
                            print(f"Response alert email sent to {creator_email} for response #{new_count}")
                        else:
                            print(f"Failed to send response alert email: {email_result.get('error')}")
                    except Exception as e:
                        print(f"Error sending response alert email: {str(e)}")

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
