import logging
import json
import os
import re
from datetime import datetime
from collections import Counter
from flask import Blueprint, jsonify, request, session, Response
from google.cloud.firestore_v1.base_query import FieldFilter
from web.utils.auth import login_required, require_form_creation
from web.extensions import db, openai_client, generate_text
from billing import get_subscription_manager
from voice_agent import create_ephemeral_token

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

# --- SCHEMAS ---

FORM_GENERATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "formId": {"type": "STRING"},
        "formTitle": {"type": "STRING"},
        "formDescription": {"type": "STRING"},
        "persona": {"type": "STRING"},
        "isEnabled": {"type": "BOOLEAN"},
        "isDeleted": {"type": "BOOLEAN"},
        "createdAt": {"type": "STRING"},
        "deletedAt": {"type": "STRING", "nullable": True},
        "latestEnabledAt": {"type": "STRING"},
        "questions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "questionKey": {"type": "STRING"},
                    "questionType": {
                        "type": "STRING", 
                        "enum": ["text", "integer", "mcq", "rating", "boolean"]
                    },
                    "source": {"type": "STRING"},
                    "sequenceNumber": {"type": "INTEGER"},
                    "questionText": {"type": "STRING"},
                    "responseDataValidationRule": {"type": "STRING"},
                    "isEnabled": {"type": "BOOLEAN"},
                    "isDeleted": {"type": "BOOLEAN"},
                    "createdAt": {"type": "STRING"},
                    "deletedAt": {"type": "STRING", "nullable": True},
                    "latestEnabledAt": {"type": "STRING"},
                    "responseOptions": {
                        "type": "OBJECT",
                        "properties": {
                            "placeholder": {"type": "STRING"},
                            "choices": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "label": {"type": "STRING"},
                                        # Updated to accept mixed types (Int, Bool, String)
                                        "value": {
                                            "anyOf": [
                                                {"type": "STRING"},
                                                {"type": "INTEGER"},
                                                {"type": "BOOLEAN"}
                                            ]
                                        }
                                    },
                                    "required": ["label", "value"]
                                }
                            }
                        }
                    }
                },
                "required": ["questionKey", "questionType", "questionText"]
            }
        }
    },
    "required": ["formTitle", "questions", "persona"]
}

# --- HELPER FUNCTIONS ---

def create_inference_prompt(input_text):
    """Create the form inference prompt focusing on intent and design"""
    return f"""You are an expert form designer and systems architect. Your goal is to analyze the unstructured input and generate a structured survey definition.

TASK:
1.  **Analyze Intent:** Understand the goal and target audience from the input.
2.  **Define Persona:** Create a distinct persona for the AI interviewer (e.g., "professional", "empathetic", "high-energy") that fits the topic.
3.  **Design Questions:** Create 5-10 effective questions using appropriate types (text, integer, mcq, rating, boolean).
4.  **Define Validation:** Write natural language validation rules for the agent to use (e.g., "Must be a valid email").

TYPE GUIDELINES:
- **text**: Open-ended questions.
- **integer**: Numeric input.
- **rating**: 0-N. ALWAYS provide explicit choices in responseOptions.choices with values 0, 1, 2, 3, 4, 5 OR 0, 1, ..., N.
- **boolean**: Yes/No.
- **mcq**: Select one/many options.

INPUT: {input_text}"""

def validate_and_fix_json(json_string):
    """Validate JSON structure and fix common issues"""
    try:
        json_string = json_string.strip()
        # Handle code blocks often returned by Gemini
        if json_string.startswith("```json"):
            json_string = json_string[7:]
        if json_string.startswith("```"):
            json_string = json_string[3:]
        if json_string.endswith("```"):
            json_string = json_string[:-3]
            
        parsed = json.loads(json_string)
        return parsed, None
    except Exception as e:
        return None, str(e)

def validate_form_generation_input(input_text):
    """Comprehensive validation for form generation input"""
    if not input_text or not input_text.strip():
        return False, "Please describe the form you want to create"
    text = input_text.strip()
    if len(text) < 20:
        return False, "Please provide more details (min 20 chars)"
    # (Simplified for brevity, re-add full regex from app.py as needed)
    return True, ""

def infer_form_from_text(input_text, max_retries=2):
    """Use configured LLM to infer form structure using Structured Output"""
    for attempt in range(max_retries + 1):
        try:
            response_text = generate_text(
                system_prompt="You are an expert form designer.",
                user_prompt=create_inference_prompt(input_text),
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=FORM_GENERATION_SCHEMA
            )
            parsed_form, error = validate_and_fix_json(response_text)
            if parsed_form:
                return parsed_form, None
        except Exception as e:
            if attempt == max_retries:
                return None, str(e)
    return None, "Unexpected error"

def refine_user_prompt(original_prompt, max_retries=2):
    """Use configured LLM to refine prompts"""
    
    # Define schema for structured output
    refined_prompt_schema = {
        "type": "OBJECT",
        "properties": {
            "refined_prompt": {"type": "STRING"}
        },
        "required": ["refined_prompt"]
    }

    for attempt in range(max_retries + 1):
        try:
            refinement_prompt = f"Refine this form generation prompt: \"{original_prompt}\""
            
            response_text = generate_text(
                system_prompt="You are a prompt optimization specialist. Return the refined prompt in JSON format.",
                user_prompt=refinement_prompt,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=refined_prompt_schema
            )
            
            # Parse the JSON response
            try:
                parsed = json.loads(response_text)
                return parsed.get("refined_prompt", "").strip(), None
            except json.JSONDecodeError:
                # Fallback if model returns raw text despite instructions
                return response_text.strip(), None
                
        except Exception as e:
            if attempt == max_retries:
                return None, str(e)
    return None, "Unexpected error"

def generate_word_frequency_backend(text_responses):
    """Generate word frequency data on the backend"""
    # Common stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "must", "shall", "can", "i", "you", "he",
        "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "her",
        "its", "our", "their", "this", "that", "these", "those",
    }

    all_words = []
    for text in text_responses:
        if text and text.strip():
            # Clean and extract words
            words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
            words = [word for word in words if word not in stop_words]
            all_words.extend(words)

    if not all_words:
        return []

    # Count word frequencies
    word_counts = Counter(all_words)

    # Return top 20 words with their frequencies
    return [
        {"word": word, "count": count} for word, count in word_counts.most_common(20)
    ]

# --- ROUTES ---

@api_bp.route("/api/infer", methods=["POST"])
@login_required
@require_form_creation
def infer_form():
    data = request.get_json()
    if not data or "dump" not in data:
        return jsonify({"success": False, "error": "Text dump required"}), 400
    
    input_text = data["dump"]
    is_valid, error_message = validate_form_generation_input(input_text)
    if not is_valid:
        return jsonify({"success": False, "error": error_message}), 400

    inferred_form, error = infer_form_from_text(input_text)
    if not inferred_form:
        return jsonify({"success": False, "error": f"Inference failed: {error}"}), 500
    
    try:
        user_id = request.user["uid"]
        now = datetime.utcnow()
        survey_data = {
            "title": inferred_form["formTitle"], # Adjusted to match schema key
            "questions": inferred_form["questions"],
            "demographics": inferred_form.get("demographics", {}),
            "creator_id": user_id,
            "active": False,
            "created_at": now,
            "last_modified": now,
            "response_count": 0,
            # Store full schema logic for reference/updates
            "formTitle": inferred_form.get("formTitle"),
            "formDescription": inferred_form.get("formDescription"),
            "persona": inferred_form.get("persona")
        }
        doc_ref = db.collection("forms").add(survey_data)
        return jsonify({
            "success": True, 
            "form": inferred_form, 
            "form_id": doc_ref[1].id
        }), 200
    except Exception as e:
        return jsonify({"success": True, "form": inferred_form, "save_error": str(e)}), 200

@api_bp.route("/api/refine_prompt", methods=["POST"])
@login_required
def refine_prompt():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"success": False, "error": "Prompt required"}), 400
    
    refined_text, error = refine_user_prompt(data["prompt"])
    if refined_text:
        return jsonify({"success": True, "refined_prompt": refined_text})
    return jsonify({"success": False, "error": error}), 500

@api_bp.route("/api/user")
@login_required
def check_user_session():
    return jsonify({
        "authenticated": True,
        "user_id": request.user["uid"],
        "email": request.user["email"],
    }), 200

@api_bp.route("/api/user/profile")
@login_required
def get_user_profile():
    try:
        user_id = request.user["uid"]
        user_doc = db.collection("users").document(user_id).get()
        if user_doc.exists:
            return jsonify({"success": True, "profile": user_doc.to_dict()}), 200
        return jsonify({"error": "User profile not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/api/health")
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

@api_bp.route("/test-session")
def test_session():
    session["test"] = "session_working"
    return jsonify({
        "session_test": session.get("test"),
        "full_session": dict(session),
        "authenticated": session.get("authenticated"),
        "user_id": session.get("user_id"),
    })

@api_bp.route("/test-openai")
@login_required
def test_openai():
    # Helper to test raw OpenAI connection if needed
    try:
        if not openai_client:
            return jsonify({"error": "OpenAI client not initialized"}), 500
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test successful' in JSON"}],
            max_tokens=50,
        )
        return jsonify({
            "success": True, 
            "response": response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/api/voice/token", methods=["POST"])
def get_voice_token():
    data = request.get_json() or {}
    voice_id = data.get("voice_id")
    form_id = data.get("form_id")
    
    if not voice_id:
        return jsonify({"success": False, "error": "voice_id required"}), 400

    language = "en"
    form_title = "Survey"
    
    if form_id:
        try:
            form_doc = db.collection("forms").document(form_id).get()
            if form_doc.exists:
                form_data = form_doc.to_dict()
                language = form_data.get("voice_settings", {}).get("language", "en")
                form_title = form_data.get("title", "Survey")
        except Exception as e:
            logger.warning(f"Could not fetch form context: {e}")

    try:
        token_info = create_ephemeral_token(voice_id, language, form_title)
        return jsonify({"success": True, **token_info})
    except Exception as e:
        logger.error(f"Error generating voice token: {e}")
        return jsonify({"success": False, "error": "Failed to generate token"}), 500

@api_bp.route("/api/save_form", methods=["POST"])
@login_required
def save_form():
    data = request.get_json()
    if not data or "form" not in data:
        return jsonify({"success": False, "error": "Form data required"}), 400
    
    form_data = data["form"]
    user_id = request.user["uid"]
    
    # Map new schema keys
    form_document = {
        "formId": form_data.get("formId", f"form_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        "formTitle": form_data.get("formTitle", form_data.get("title", "Untitled")),
        "formDescription": form_data.get("formDescription", ""),
        "persona": form_data.get("persona", form_data.get("bot_context", "")),
        "questions": form_data.get("questions", []),
        "demographics": form_data.get("demographics", {}),
        "profile_data": form_data.get("profile_data", {}),
        "creator_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "isEnabled": True,
        "active": True,
        "response_count": 0,
        "mode": form_data.get("mode", "chat"),
        "voice_settings": form_data.get("voice_settings", {})
    }
    
    form_ref = db.collection("forms").document()
    form_ref.set(form_document)
    
    return jsonify({
        "success": True, 
        "form_id": form_ref.id, 
        "share_url": f"barmuda.in/form/{form_ref.id}"
    }), 200

@api_bp.route("/api/update_form/<form_id>", methods=["PUT"])
@login_required
def update_form(form_id):
    try:
        data = request.get_json()
        if not data or "form" not in data:
            return jsonify({"success": False, "error": "Form data required"}), 400

        form_data = data["form"]
        user_id = request.user["uid"]

        form_ref = db.collection("forms").document(form_id)
        form_doc = form_ref.get()

        if not form_doc.exists:
            return jsonify({"success": False, "error": "Form not found"}), 404

        existing_form = form_doc.to_dict()
        if existing_form.get("creator_id") != user_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        # Update with new schema
        update_document = {
            "formTitle": form_data.get("formTitle", form_data.get("title", existing_form.get("formTitle"))),
            "formDescription": form_data.get("formDescription", existing_form.get("formDescription", "")),
            "persona": form_data.get("persona", form_data.get("bot_context", existing_form.get("persona"))),
            "questions": form_data.get("questions", existing_form.get("questions", [])),
            "demographics": form_data.get("demographics", existing_form.get("demographics", {})),
            "profile_data": form_data.get("profile_data", existing_form.get("profile_data", {})),
            "active": form_data.get("active", existing_form.get("active", False)),
            "last_modified": datetime.utcnow(),
            "updated_at": datetime.utcnow().isoformat(),
            "mode": form_data.get("mode", existing_form.get("mode", "chat")),
            "voice_settings": form_data.get("voice_settings", existing_form.get("voice_settings", {}))
        }
        
        form_ref.update(update_document)
        return jsonify({"success": True, "form_id": form_id}), 200
        
    except Exception as e:
        logger.error(f"Error updating form: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route("/api/form/<form_id>")
@login_required
def get_form(form_id):
    try:
        user_id = request.user["uid"]
        form_ref = db.collection("forms").document(form_id)
        form_doc = form_ref.get()

        if not form_doc.exists:
            return jsonify({"success": False, "error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != user_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        return jsonify({
            "success": True,
            "form": form_data,
            "metadata": {
                "form_id": form_id,
                "created_at": form_data.get("created_at"),
                "status": form_data.get("status")
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route("/api/responses/<form_id>")
@login_required
def get_form_responses(form_id):
    """Get all responses for a form from the 'sessions' collection"""
    try:
        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return jsonify({"error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != request.user["uid"]:
            return jsonify({"error": "Unauthorized"}), 403

        # Get responses from 'sessions' collection
        responses_query = (
            db.collection("sessions")
            .where(filter=FieldFilter("form_id", "==", form_id))
            .stream()
        )
        responses = []

        for response_doc in responses_query:
            response_data = response_doc.to_dict()
            # Handle created_at field - might be datetime object or string
            created_at = response_data.get("created_at")
            if created_at:
                if hasattr(created_at, "isoformat"):
                    created_at = created_at.isoformat()

            responses.append(
                {
                    "id": response_doc.id,
                    "responses": response_data.get("responses", {}),
                    "metadata": response_data.get("metadata", {}),
                    "created_at": created_at,
                    "partial": response_data.get("session_state") != "FINISHED",
                    "mode": response_data.get("mode", "chat"),
                }
            )

        return jsonify(
            {
                "form_title": form_data.get("title", "Untitled Form"),
                "responses": responses,
                "total_responses": len(responses),
            }
        )

    except Exception as e:
        logger.error(f"Error getting responses: {str(e)}")
        return jsonify({"error": "Failed to fetch responses"}), 500


@api_bp.route("/api/wordcloud/<form_id>/<int:question_index>")
@login_required
def generate_wordcloud(form_id, question_index):
    """Generate word cloud data for text questions using the 'sessions' collection"""
    try:
        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return jsonify({"error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != request.user["uid"]:
            return jsonify({"error": "Unauthorized"}), 403

        # Find the question key for this index
        questions = form_data.get("questions", [])
        if question_index >= len(questions):
            return jsonify({"error": "Question index out of range"}), 400
        
        target_question_key = questions[question_index].get("questionKey")

        # Get responses for this question from 'sessions'
        responses_query = (
            db.collection("sessions")
            .where(filter=FieldFilter("form_id", "==", form_id))
            .stream()
        )
        text_responses = []

        for response_doc in responses_query:
            response_data = response_doc.to_dict()
            if "responses" in response_data:
                # Check both questionKey and legacy index string
                answer = response_data["responses"].get(target_question_key) or \
                         response_data["responses"].get(str(question_index))
                
                if answer and answer.get("value") and str(answer.get("value")) not in ["[SKIP]", "[ABANDONED]"]:
                    text_responses.append(str(answer.get("value")))

        # Generate word frequency data
        word_freq = generate_word_frequency_backend(text_responses)

        return jsonify(
            {
                "success": True,
                "word_frequency": word_freq,
                "total_responses": len(text_responses),
            }
        )

    except Exception as e:
        logger.error(f"Error generating word cloud: {str(e)}")
        return jsonify({"error": "Failed to generate word cloud"}), 500


@api_bp.route("/api/export/<form_id>/<format>")
@login_required
def export_responses(form_id, format):
    """Export responses from 'sessions' in JSON or CSV format"""
    try:
        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return jsonify({"error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != request.user["uid"]:
            return jsonify({"error": "Unauthorized"}), 403

        # Get responses from 'sessions'
        responses_query = (
            db.collection("sessions")
            .where(filter=FieldFilter("form_id", "==", form_id))
            .stream()
        )
        responses = []

        for response_doc in responses_query:
            response_data = response_doc.to_dict()
            responses.append(response_data)

        if format.lower() == "json":
            return Response(
                json.dumps(responses, indent=2, default=str),
                mimetype="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=responses_{form_id}.json"
                },
            )

        elif format.lower() == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            if responses:
                # Get all possible field names
                fieldnames = set()
                for r in responses:
                    fieldnames.update(r.keys())
                    if "responses" in r:
                        for q_key in r["responses"]:
                            fieldnames.add(f"Answer_{q_key}")
                
                # Sort fields for consistency
                sorted_fields = sorted(list(fieldnames))
                
                writer = csv.DictWriter(output, fieldnames=sorted_fields)
                writer.writeheader()
                
                for r in responses:
                    row = {}
                    # Copy flat fields
                    for k, v in r.items():
                        if k != "responses":
                            row[k] = str(v)
                    
                    # Flatten responses
                    if "responses" in r:
                        for q_key, q_data in r["responses"].items():
                            row[f"Answer_{q_key}"] = q_data.get("value")
                    writer.writerow(row)

            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=responses_{form_id}.csv"
                },
            )
        
        return jsonify({"error": "Invalid format"}), 400

    except Exception as e:
        logger.error(f"Error exporting responses: {str(e)}")
        return jsonify({"error": "Export failed"}), 500
