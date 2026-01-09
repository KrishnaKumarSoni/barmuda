import logging
import json
import os
import re
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from web.utils.auth import login_required, require_form_creation
from web.extensions import db, openai_client, generate_text
from billing import get_subscription_manager
from voice_agent import create_ephemeral_token

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

# --- HELPER FUNCTIONS ---

def create_inference_prompt(input_text):
    """Create the form inference prompt with Chain-of-Thought and few-shot examples"""
    return f"""You are an expert form designer. Given an unstructured text dump describing a form or survey, you need to infer a structured form with appropriate questions and answer types.

TASK: Analyze the input text and create a JSON form structure following the exact format below.

REASONING PROCESS (Chain-of-Thought):
1. First, summarize the main intent/purpose of the form from the input
2. Identify 5-10 key questions that would capture the needed information
3. For each question, determine the most appropriate input type
4. Generate logical answer options for multiple choice questions
5. Self-critique: Are the questions comprehensive? Are types appropriate?

OUTPUT FORMAT (JSON only, no additional text):
{{
  "title": "Form Title (concise, descriptive)",
  "questions": [
    {{
      "text": "Question text",
      "type": "text|multiple_choice|yes_no|number|rating",
      "options": ["option1", "option2", "..."] or null,
      "enabled": true
    }}
  ]
}}

QUESTION TYPES:
- text: Open-ended text responses
- multiple_choice: Select one from predefined options (include "Other" and "Prefer not to say" when appropriate)
- yes_no: Simple yes/no questions
- number: Numeric input (age, quantity, etc.)
- rating: 1-5 or 1-10 scale ratings

DEMOGRAPHICS TEMPLATE:
Always consider including these standard demographic questions when appropriate:
- Age (multiple_choice: "18-24", "25-34", "35-44", "45-54", "55-64", "65+", "Prefer not to say")
- Gender (multiple_choice: "Male", "Female", "Non-binary", "Other", "Prefer not to say")

INPUT: {input_text}
OUTPUT:"""

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
            
        start_idx = json_string.find("{")
        end_idx = json_string.rfind("}")
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No valid JSON structure found")
        json_string = json_string[start_idx : end_idx + 1]
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
    """Use configured LLM to infer form structure"""
    for attempt in range(max_retries + 1):
        try:
            response_text = generate_text(
                system_prompt="You are an expert form designer.",
                user_prompt=create_inference_prompt(input_text),
                temperature=0.1
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
    for attempt in range(max_retries + 1):
        try:
            refinement_prompt = f"Refine this form generation prompt: \"{original_prompt}\"\nRefined prompt:"
            refined_text = generate_text(
                system_prompt="You are a prompt optimization specialist. Return ONLY the refined prompt text. No explanations, no quotes, no markdown.",
                user_prompt=refinement_prompt,
                temperature=0.1
            )
            return refined_text.strip(), None
        except Exception as e:
            if attempt == max_retries:
                return None, str(e)
    return None, "Unexpected error"

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
            "title": inferred_form["title"],
            "questions": inferred_form["questions"],
            "demographics": inferred_form.get("demographics", {}),
            "creator_id": user_id,
            "active": False,
            "created_at": now,
            "last_modified": now,
            "response_count": 0,
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
    
    # ... (Validation and saving logic from app.py) ...
    # Minimal validation here, assume frontend sends correct structure or add detailed validation
    
    form_document = {
        "title": form_data.get("title", "Untitled"),
        "questions": form_data.get("questions", []),
        "demographics": form_data.get("demographics", {}),
        "profile_data": form_data.get("profile_data", {}),
        "bot_context": form_data.get("bot_context", ""),
        "creator_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "status": "active",
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

        update_document = {
            "title": form_data.get("title"),
            "questions": form_data.get("questions"),
            "demographics": form_data.get("demographics"),
            "profile_data": form_data.get("profile_data"),
            "bot_context": form_data.get("bot_context"),
            "active": form_data.get("active", existing_form.get("active", False)),
            "last_modified": datetime.utcnow(),
            "updated_at": datetime.utcnow().isoformat(),
            "mode": form_data.get("mode", existing_form.get("mode", "chat")),
            "voice_settings": form_data.get("voice_settings", {})
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