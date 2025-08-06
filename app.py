import json
import logging
import os
import re
from datetime import datetime
from functools import wraps

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import auth, credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from flask import Flask, jsonify, redirect, render_template, request, session, url_for, send_from_directory, Response
from flask_cors import CORS
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "dev-secret-key-for-local-testing-very-long-and-secure-123456789",
)

# Configure session
app.config["SESSION_COOKIE_SECURE"] = False  # Allow HTTP for localhost
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CORS(app, supports_credentials=True)


# Make config available to templates
@app.context_processor
def inject_config():
    return dict(config=os.environ)


# Make user session data available to templates
@app.context_processor
def inject_user():
    if session.get("authenticated") and session.get("user_id"):
        return dict(
            request={
                "user": {
                    "uid": session.get("user_id"),
                    "email": session.get("email", ""),
                    "user_id": session.get("user_id"),
                }
            }
        )
    return dict(request={"user": None})


# Add custom Jinja2 filter for JSON serialization
@app.template_filter("tojsonfilter")
def to_json_filter(obj):
    import json

    from markupsafe import Markup

    return Markup(json.dumps(obj))


# Favicon route - serve ICO file
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static/assets'),
        'favicon.ico',
        mimetype='image/x-icon'
    )


# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    # For production (Vercel), use environment variables
    # For local development, fall back to service account file
    if os.environ.get("VERCEL") or os.environ.get("FIREBASE_PRIVATE_KEY"):
        # Production environment - use environment variables
        firebase_config = {
            "type": "service_account",
            "project_id": os.environ.get("FIREBASE_PROJECT_ID", "bermuda-01"),
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace(
                "\\n", "\n"
            ),
            "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('FIREBASE_CLIENT_EMAIL', '').replace('@', '%40')}",
            "universe_domain": "googleapis.com",
        }
        cred = credentials.Certificate(firebase_config)
    else:
        # Local development - use service account file
        cred = credentials.Certificate(
            "barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json"
        )

    firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

# Initialize OpenAI client - strip whitespace from API key to prevent header errors
openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
openai_client = OpenAI(api_key=openai_api_key)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for session authentication
        if not session.get("authenticated") or not session.get("user_id"):
            if request.is_json:
                return jsonify({"error": "Authentication required"}), 401
            else:
                return redirect("/")

        # Add user info to request for compatibility
        request.user = {
            "uid": session.get("user_id"),
            "email": session.get("email", ""),
            "user_id": session.get("user_id"),
        }

        return f(*args, **kwargs)

    return decorated_function


# Form Inference Logic
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

DEMOGRAPHICS TEMPLATE (add relevant ones based on context):
Always consider including these standard demographic questions when appropriate:
- Age (multiple_choice: "18-24", "25-34", "35-44", "45-54", "55-64", "65+", "Prefer not to say")
- Gender (multiple_choice: "Male", "Female", "Non-binary", "Other", "Prefer not to say")
- Location (text or multiple_choice based on scope)
- Education Level (multiple_choice: "High School", "Bachelor's", "Master's", "PhD", "Other", "Prefer not to say")
- Employment Status (multiple_choice: "Employed", "Student", "Unemployed", "Retired", "Other", "Prefer not to say")

FEW-SHOT EXAMPLES:

INPUT: "I want to survey coffee preferences, favorite drinks, and satisfaction ratings"
OUTPUT:
{{
  "title": "Coffee Preferences Survey",
  "questions": [
    {{
      "text": "How often do you drink coffee?",
      "type": "multiple_choice",
      "options": ["Daily", "Several times a week", "Weekly", "Rarely", "Never"],
      "enabled": true
    }},
    {{
      "text": "What is your favorite type of coffee drink?",
      "type": "multiple_choice", 
      "options": ["Espresso", "Americano", "Latte", "Cappuccino", "Cold Brew", "Frappuccino", "Other"],
      "enabled": true
    }},
    {{
      "text": "Rate your overall satisfaction with your usual coffee shop",
      "type": "rating",
      "options": ["1", "2", "3", "4", "5"],
      "enabled": true
    }},
    {{
      "text": "What factors are most important when choosing coffee?",
      "type": "multiple_choice",
      "options": ["Taste", "Price", "Convenience", "Brand", "Health benefits", "Other"],
      "enabled": true
    }},
    {{
      "text": "Any additional comments about your coffee preferences?",
      "type": "text",
      "options": null,
      "enabled": true
    }},
    {{
      "text": "What is your age range?",
      "type": "multiple_choice",
      "options": ["18-24", "25-34", "35-44", "45-54", "55-64", "65+", "Prefer not to say"],
      "enabled": true
    }}
  ]
}}

INPUT: "Event feedback form - venue, speakers, networking, overall rating"
OUTPUT:
{{
  "title": "Event Feedback Survey",
  "questions": [
    {{
      "text": "How would you rate the event venue?",
      "type": "rating",
      "options": ["1", "2", "3", "4", "5"],
      "enabled": true
    }},
    {{
      "text": "How would you rate the quality of speakers?",
      "type": "rating",
      "options": ["1", "2", "3", "4", "5"],
      "enabled": true
    }},
    {{
      "text": "Which speaker did you find most valuable?",
      "type": "text",
      "options": null,
      "enabled": true
    }},
    {{
      "text": "How was the networking experience?",
      "type": "multiple_choice",
      "options": ["Excellent", "Good", "Average", "Poor", "Did not participate"],
      "enabled": true
    }},
    {{
      "text": "What was your overall rating of the event?",
      "type": "rating",
      "options": ["1", "2", "3", "4", "5"],
      "enabled": true
    }},
    {{
      "text": "Would you attend this event again?",
      "type": "yes_no",
      "options": null,
      "enabled": true
    }},
    {{
      "text": "What could be improved for next time?",
      "type": "text",
      "options": null,
      "enabled": true
    }},
    {{
      "text": "How did you hear about this event?",
      "type": "multiple_choice",
      "options": ["Social media", "Email", "Website", "Friend/colleague", "Advertisement", "Other"],
      "enabled": true
    }}
  ]
}}

INPUT: "Job application: background, experience, skills, availability"
OUTPUT:
{{
  "title": "Job Application Form",
  "questions": [
    {{
      "text": "What is your educational background?",
      "type": "multiple_choice",
      "options": ["High School", "Associate Degree", "Bachelor's Degree", "Master's Degree", "PhD", "Other"],
      "enabled": true
    }},
    {{
      "text": "How many years of relevant work experience do you have?",
      "type": "multiple_choice",
      "options": ["Less than 1 year", "1-2 years", "3-5 years", "5-10 years", "10+ years"],
      "enabled": true
    }},
    {{
      "text": "Please describe your most relevant work experience",
      "type": "text",
      "options": null,
      "enabled": true
    }},
    {{
      "text": "What key skills do you bring to this role?",
      "type": "text",
      "options": null,
      "enabled": true
    }},
    {{
      "text": "Are you available to start immediately?",
      "type": "yes_no",
      "options": null,
      "enabled": true
    }},
    {{
      "text": "What is your preferred work arrangement?",
      "type": "multiple_choice",
      "options": ["Full-time in office", "Full-time remote", "Hybrid", "Part-time", "Contract", "Flexible"],
      "enabled": true
    }},
    {{
      "text": "Expected salary range",
      "type": "text",
      "options": null,
      "enabled": true
    }},
    {{
      "text": "Why are you interested in this position?",
      "type": "text",
      "options": null,
      "enabled": true
    }}
  ]
}}

Now analyze this input and create a structured form:

INPUT: {input_text}
OUTPUT:"""


def validate_and_fix_json(json_string):
    """Validate JSON structure and fix common issues"""
    try:
        # Clean up the response - remove any extra text before/after JSON
        json_string = json_string.strip()

        # Find JSON boundaries
        start_idx = json_string.find("{")
        end_idx = json_string.rfind("}")

        if start_idx == -1 or end_idx == -1:
            raise ValueError("No valid JSON structure found")

        json_string = json_string[start_idx : end_idx + 1]

        # Parse JSON
        parsed = json.loads(json_string)

        # Validate required fields
        if "title" not in parsed:
            raise ValueError("Missing 'title' field")
        if "questions" not in parsed or not isinstance(parsed["questions"], list):
            raise ValueError("Missing or invalid 'questions' field")

        # Validate each question
        valid_types = ["text", "multiple_choice", "yes_no", "number", "rating"]
        for i, question in enumerate(parsed["questions"]):
            if "text" not in question:
                raise ValueError(f"Question {i+1} missing 'text' field")
            if "type" not in question or question["type"] not in valid_types:
                raise ValueError(f"Question {i+1} has invalid or missing 'type' field")
            if "enabled" not in question:
                question["enabled"] = True

            # Validate options for multiple_choice and rating
            if question["type"] in ["multiple_choice", "rating"]:
                if "options" not in question or not isinstance(
                    question["options"], list
                ):
                    raise ValueError(
                        f"Question {i+1} of type '{question['type']}' requires 'options' list"
                    )
                if len(question["options"]) < 2:
                    raise ValueError(f"Question {i+1} needs at least 2 options")
            elif question["type"] in ["text", "yes_no", "number"]:
                question["options"] = None

        return parsed, None

    except json.JSONDecodeError as e:
        return None, f"Invalid JSON format: {str(e)}"
    except ValueError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Validation error: {str(e)}"


def infer_form_from_text(input_text, max_retries=2):
    """Use OpenAI GPT-4o-mini to infer form structure from unstructured text"""

    # Debug API key availability
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not found!")
        return None, "OpenAI API key not configured"

    logger.info(
        f"Using OpenAI API key: {api_key[:8]}...{api_key[-8:] if len(api_key) > 16 else ''}"
    )

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                f"Form inference attempt {attempt + 1} for input: {input_text[:100]}..."
            )

            # Generate response using OpenAI client
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert form designer. Create structured JSON forms from unstructured text descriptions.",
                    },
                    {"role": "user", "content": create_inference_prompt(input_text)},
                ],
                temperature=0.1,
                max_tokens=2000,
            )

            response_text = response.choices[0].message.content
            logger.info(
                f"LLM response (attempt {attempt + 1}): {response_text[:200]}..."
            )

            # Validate and parse JSON
            parsed_form, error = validate_and_fix_json(response_text)

            if parsed_form:
                logger.info(
                    f"Successfully inferred form with {len(parsed_form['questions'])} questions"
                )
                return parsed_form, None
            else:
                logger.warning(f"Attempt {attempt + 1} failed validation: {error}")
                if attempt == max_retries:
                    return (
                        None,
                        f"Failed to generate valid form after {max_retries + 1} attempts. Last error: {error}",
                    )

        except Exception as e:
            import traceback

            logger.error(f"Attempt {attempt + 1} failed with exception: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if attempt == max_retries:
                return (
                    None,
                    f"Form inference failed after {max_retries + 1} attempts: {str(e)}",
                )

    return None, "Unexpected error in form inference"


# Routes


@app.route("/")
def home():
    """Home page - redirect authenticated users to create-form, show anonymous landing otherwise"""
    # Debug session state
    logger.info(f"Home route - Session: {dict(session)}")
    logger.info(
        f"Authenticated: {session.get('authenticated')}, User ID: {session.get('user_id')}"
    )

    # Check if user is authenticated
    if session.get("authenticated") and session.get("user_id"):
        logger.info("User is authenticated, redirecting to create-form")
        return redirect(url_for("create_form"))

    # For unauthenticated users, show the anonymous landing page
    logger.info("User not authenticated, showing anonymous landing page")
    return render_template("index.html")


@app.route("/test-session")
def test_session():
    """Test route to debug session functionality"""
    session["test"] = "session_working"
    return jsonify(
        {
            "session_test": session.get("test"),
            "full_session": dict(session),
            "authenticated": session.get("authenticated"),
            "user_id": session.get("user_id"),
        }
    )


@app.route("/test-openai")
@login_required
def test_openai():
    """Test route to debug OpenAI API connectivity in production"""
    try:
        # Check environment variables
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return (
                jsonify(
                    {
                        "error": "OPENAI_API_KEY not found in environment",
                        "env_vars": list(os.environ.keys()),
                    }
                ),
                500,
            )

        # Test simple OpenAI call
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'test successful' in JSON format"}
            ],
            max_tokens=50,
        )

        return jsonify(
            {
                "success": True,
                "response": response.choices[0].message.content,
                "api_key_present": bool(api_key),
                "api_key_prefix": api_key[:8] + "..." if api_key else None,
            }
        )

    except Exception as e:
        import traceback

        return (
            jsonify(
                {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
                }
            ),
            500,
        )


@app.route("/auth/google", methods=["POST"])
def google_auth():
    """Handle real Google Firebase authentication"""
    try:
        # Get the ID token from the request
        data = request.get_json()
        if not data or "idToken" not in data:
            return jsonify({"error": "ID token is required"}), 400

        id_token = data["idToken"]

        # Verify the ID token with Firebase
        decoded_token = auth.verify_id_token(id_token)

        # Extract user information
        user_id = decoded_token["uid"]
        email = decoded_token.get("email", "")
        name = decoded_token.get("name", "")

        # Check if user exists in Firestore
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            # Create new user profile
            user_data = {
                "user_id": user_id,
                "email": email,
                "name": name,
                "created_at": datetime.now().isoformat(),
            }
            user_ref.set(user_data)
            logger.info(f"Created new user: {email}")
        else:
            logger.info(f"User login: {email}")

        # Store user session
        session["user_id"] = user_id
        session["email"] = email
        session["authenticated"] = True

        # Debug session after setting
        logger.info(f"After setting session - Session: {dict(session)}")
        logger.info(f"Session authenticated: {session.get('authenticated')}")

        return jsonify(
            {
                "success": True,
                "user": {"user_id": user_id, "email": email, "name": name},
            }
        )

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({"error": "Authentication failed", "details": str(e)}), 401


@app.route("/auth/logout", methods=["POST"])
def logout():
    """Handle logout"""
    session.clear()
    return jsonify({"success": True})


@app.route("/auth/verify", methods=["POST"])
def verify_token():
    """Verify if a token is valid"""
    try:
        data = request.get_json()
        if not data or "idToken" not in data:
            return jsonify({"error": "ID token is required"}), 400

        id_token = data["idToken"]
        decoded_token = auth.verify_id_token(id_token)

        return (
            jsonify(
                {
                    "valid": True,
                    "user": {
                        "user_id": decoded_token["uid"],
                        "email": decoded_token.get("email", ""),
                        "name": decoded_token.get("name", ""),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 401


@app.route("/dashboard")
@login_required
def dashboard():
    """Protected dashboard route"""
    try:
        user_id = request.user["uid"]

        # Get user's forms with response counts
        try:
            # Try to get forms ordered by creation date (newest first) - requires composite index
            forms_ref = db.collection("forms").where(filter=FieldFilter("creator_id", "==", user_id)).order_by("created_at", direction=firestore.Query.DESCENDING)
            forms = []
            for doc in forms_ref.stream():
                form_data = doc.to_dict()
                form_data["form_id"] = doc.id

                # Count responses for this form
                responses_ref = db.collection("responses").where(filter=FieldFilter("form_id", "==", doc.id))
                response_count = len(list(responses_ref.stream()))
                form_data["response_count"] = response_count

                forms.append(form_data)
        except Exception as index_error:
            # Fallback: Get forms without ordering if composite index doesn't exist yet
            print(f"Composite index not available, falling back to unordered query: {index_error}")
            forms_ref = db.collection("forms").where(filter=FieldFilter("creator_id", "==", user_id))
            forms = []
            for doc in forms_ref.stream():
                form_data = doc.to_dict()
                form_data["form_id"] = doc.id

                # Count responses for this form
                responses_ref = db.collection("responses").where(filter=FieldFilter("form_id", "==", doc.id))
                response_count = len(list(responses_ref.stream()))
                form_data["response_count"] = response_count

                forms.append(form_data)
            
            # Sort in Python as fallback (less efficient but works without index)
            forms.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)

        return render_template("dashboard.html", forms=forms, user=request.user)

    except Exception as e:
        return jsonify({"error": "Failed to load dashboard", "details": str(e)}), 500


@app.route("/api/user/profile")
@login_required
def get_user_profile():
    """Get current user's profile"""
    try:
        user_id = request.user["uid"]
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            return jsonify({"success": True, "profile": user_doc.to_dict()}), 200
        else:
            return jsonify({"error": "User profile not found"}), 404

    except Exception as e:
        return jsonify({"error": "Failed to get profile", "details": str(e)}), 500


def validate_form_generation_input(input_text):
    """
    Comprehensive validation for form generation input
    Returns: (is_valid, error_message)
    """
    import re

    # Basic checks
    if not input_text or not input_text.strip():
        return False, "Please describe the form you want to create"

    text = input_text.strip()

    # Length checks
    if len(text) < 20:
        return (
            False,
            "Please provide more details about your form (minimum 20 characters)",
        )

    if len(text) > 5000:
        return False, "Description too long (maximum 5000 characters)"

    # Content quality checks
    if (
        not re.search(r"\S", text)
        or len(text.replace(" ", "").replace("\n", "").replace("\t", "")) < 10
    ):
        return False, "Please provide a meaningful description"

    # Repetitive content detection
    if re.search(r"(.)\1{6,}", text):
        return False, "Please provide a meaningful description of your form"

    # Keyboard mashing detection
    keyboard_patterns = [
        r"^[qwertyuiop\s]+$",
        r"^[asdfghjkl\s]+$",
        r"^[zxcvbnm\s]+$",
        r"^[1234567890\s]+$",
    ]

    text_no_spaces = re.sub(r"\s+", "", text.lower())
    for pattern in keyboard_patterns:
        if len(text_no_spaces) > 10 and re.match(pattern, text_no_spaces):
            return (
                False,
                "Please provide a real description of the form you want to create",
            )

    # Prompt injection detection
    injection_patterns = [
        r"\b(ignore|forget|disregard).{0,20}(previous|above|instruction|prompt|system)",
        r"(system|assistant|user):\s",
        r"\b(execute|run|command|script)\b",
        r"</?(script|iframe|object|embed)",
        r"\b(hack|exploit|inject|bypass)\b",
        r"(you are|act as|pretend to be|roleplay)",
        r"\b(jailbreak|prompt.?injection)\b",
    ]

    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return (
                False,
                "Invalid input detected. Please describe your form requirements clearly.",
            )

    # Form-related content validation
    form_keywords = [
        "form",
        "survey",
        "question",
        "data",
        "collect",
        "response",
        "feedback",
        "poll",
        "quiz",
        "assessment",
        "evaluation",
        "information",
        "details",
        "input",
        "field",
        "answer",
        "customer",
        "user",
        "participant",
        "research",
        "study",
        "opinion",
        "rating",
        "review",
        "contact",
        "registration",
        "application",
    ]

    non_form_keywords = [
        "weather",
        "time",
        "date",
        "news",
        "sports",
        "movie",
        "music",
        "food",
        "recipe",
        "game",
        "joke",
        "story",
        "entertainment",
        "celebrity",
        "politics",
        "shopping",
        "travel",
        "hotel",
        "restaurant",
        "directions",
        "navigation",
    ]

    # Check if it contains form-related content
    has_form_keywords = any(keyword in text.lower() for keyword in form_keywords)
    has_non_form_keywords = any(
        keyword in text.lower() for keyword in non_form_keywords
    )

    # Reject if it has non-form keywords without form keywords
    if has_non_form_keywords and not has_form_keywords:
        return (
            False,
            "This doesn't seem to be about creating a form. Please describe your survey goals and what data you want to collect.",
        )

    # Reject if it doesn't have any form keywords at all (more strict validation)
    if not has_form_keywords:
        return (
            False,
            "Please describe what kind of form or survey you want to create, what data you want to collect, or what questions you want to ask.",
        )

    # Inappropriate content detection (basic)
    inappropriate_patterns = [
        r"\b(hate|kill|murder|violence|terrorist|bomb)\b",
        r"\b(porn|sex|adult|nude|explicit)\b",
        r"\b(drug|cocaine|heroin|marijuana)\b",
        r"\b(scam|fraud|steal|money.?laundering)\b",
    ]

    for pattern in inappropriate_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return (
                False,
                "Cannot create forms for inappropriate content. Please describe a legitimate survey or data collection need.",
            )

    return True, ""


@app.route("/api/infer", methods=["POST"])
@login_required
def infer_form():
    """
    Infer form structure from unstructured text dump with comprehensive validation

    Expected JSON payload:
    {
        "dump": "text describing the form/survey"
    }

    Returns:
    {
        "success": true,
        "form": {
            "title": "Form Title",
            "questions": [...]
        }
    }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data or "dump" not in data:
            return (
                jsonify(
                    {"success": False, "error": "Text dump is required in request body"}
                ),
                400,
            )

        input_text = data["dump"]

        # Comprehensive validation
        is_valid, error_message = validate_form_generation_input(input_text)
        if not is_valid:
            logger.warning(
                f"Form generation validation failed for user {request.user['uid']}: {error_message}"
            )
            return jsonify({"success": False, "error": error_message}), 400

        input_text = input_text.strip()

        logger.info(
            f"Form inference requested by user {request.user['uid']} for: {input_text[:100]}..."
        )

        # Infer form structure using LLM
        inferred_form, error = infer_form_from_text(input_text)

        if inferred_form:
            logger.info(f"Successfully inferred form: {inferred_form['title']}")

            # Auto-save the generated survey as inactive
            try:
                user_id = request.user["uid"]
                now = datetime.utcnow()

                # Create inactive survey document
                survey_data = {
                    "title": inferred_form["title"],
                    "questions": inferred_form["questions"],
                    "demographics": inferred_form.get("demographics", {}),
                    "creator_id": user_id,
                    "active": False,  # Key field - survey is inactive
                    "created_at": now,
                    "last_modified": now,
                    "original_input": input_text,
                    "response_count": 0,
                    "share_url": None,  # Will be set when activated
                }

                # Save to Firebase
                doc_ref = db.collection("forms").add(survey_data)
                form_id = doc_ref[1].id

                logger.info(f"Auto-saved inactive survey {form_id} for user {user_id}")

                return (
                    jsonify(
                        {
                            "success": True,
                            "form": inferred_form,
                            "form_id": form_id,  # Return the Firebase ID
                            "metadata": {
                                "input_length": len(input_text),
                                "questions_count": len(inferred_form["questions"]),
                                "created_at": now.isoformat(),
                                "auto_saved": True,
                            },
                        }
                    ),
                    200,
                )

            except Exception as save_error:
                logger.error(f"Failed to auto-save survey: {str(save_error)}")
                # Still return the form data even if save fails
                return (
                    jsonify(
                        {
                            "success": True,
                            "form": inferred_form,
                            "form_id": None,
                            "metadata": {
                                "input_length": len(input_text),
                                "questions_count": len(inferred_form["questions"]),
                                "created_at": datetime.utcnow().isoformat(),
                                "auto_saved": False,
                                "save_error": str(save_error),
                            },
                        }
                    ),
                    200,
                )
        else:
            logger.error(f"Form inference failed: {error}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Failed to infer form structure: {error}",
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Unexpected error in /api/infer: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Internal server error during form inference",
                }
            ),
            500,
        )


@app.route("/create-form")
@login_required
def create_form():
    """Form creation page"""
    return render_template("create_form.html", user=request.user)


@app.route("/pricing")
def pricing():
    """Pricing page"""
    return render_template("pricing.html")


@app.route("/edit-form")
@login_required
def edit_form():
    """Form editing page"""
    return render_template("edit_form.html", user=request.user)


@app.route("/api/save_form", methods=["POST"])
@login_required
def save_form():
    """
    Save form to Firestore and generate form_id

    Expected JSON payload:
    {
        "form": {
            "title": "Form Title",
            "questions": [...],
            "demographics": {...}
        }
    }

    Returns:
    {
        "success": true,
        "form_id": "generated_form_id",
        "share_url": "bermuda.app/form/{form_id}"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data or "form" not in data:
            return jsonify({"success": False, "error": "Form data is required"}), 400

        form_data = data["form"]
        user_id = request.user["uid"]

        # Validate form data
        if not form_data.get("title"):
            return jsonify({"success": False, "error": "Form title is required"}), 400

        if not form_data.get("questions") or not isinstance(
            form_data["questions"], list
        ):
            return (
                jsonify(
                    {"success": False, "error": "Form must have at least one question"}
                ),
                400,
            )

        # Check for at least one enabled question
        enabled_questions = [
            q for q in form_data["questions"] if q.get("enabled", True)
        ]
        if not enabled_questions:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Form must have at least one enabled question",
                    }
                ),
                400,
            )

        # Validate each question
        for i, question in enumerate(form_data["questions"]):
            if not question.get("text"):
                return (
                    jsonify(
                        {"success": False, "error": f"Question {i+1} must have text"}
                    ),
                    400,
                )

            if question.get("type") not in [
                "text",
                "multiple_choice",
                "yes_no",
                "number",
                "rating",
            ]:
                return (
                    jsonify(
                        {"success": False, "error": f"Question {i+1} has invalid type"}
                    ),
                    400,
                )

            # Validate options for multiple choice and rating questions
            if question.get("type") in ["multiple_choice", "rating"]:
                if not question.get("options") or len(question["options"]) < 2:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": f"Question {i+1} must have at least 2 options",
                            }
                        ),
                        400,
                    )

        # Prepare form document
        form_document = {
            "title": form_data["title"],
            "questions": form_data["questions"],
            "demographics": form_data.get("demographics", {}),
            "creator_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "status": "active",
            "response_count": 0,
        }

        logger.info(f"Saving form '{form_data['title']}' for user {user_id}")

        # Save to Firestore
        form_ref = db.collection("forms").document()
        form_ref.set(form_document)
        form_id = form_ref.id

        logger.info(f"Form saved successfully with ID: {form_id}")

        # Generate share URL
        share_url = f"barmuda.vercel.app/form/{form_id}"

        return (
            jsonify(
                {
                    "success": True,
                    "form_id": form_id,
                    "share_url": share_url,
                    "metadata": {
                        "questions_count": len(form_data["questions"]),
                        "enabled_questions": len(enabled_questions),
                        "demographics_enabled": len(
                            [
                                k
                                for k, v in form_data.get("demographics", {}).items()
                                if v
                            ]
                        ),
                        "created_at": form_document["created_at"],
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error saving form: {str(e)}")
        return (
            jsonify(
                {"success": False, "error": "Internal server error while saving form"}
            ),
            500,
        )


@app.route("/api/update_form/<form_id>", methods=["PUT"])
@login_required
def update_form(form_id):
    """
    Update existing form in Firestore

    Expected JSON payload:
    {
        "form": {
            "title": "Form Title",
            "questions": [...],
            "demographics": {...}
        }
    }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data or "form" not in data:
            return jsonify({"success": False, "error": "Form data is required"}), 400

        form_data = data["form"]
        user_id = request.user["uid"]

        # Get existing form to verify ownership
        form_ref = db.collection("forms").document(form_id)
        form_doc = form_ref.get()

        if not form_doc.exists:
            return jsonify({"success": False, "error": "Form not found"}), 404

        existing_form = form_doc.to_dict()

        # Check if user owns this form
        if existing_form.get("creator_id") != user_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        # Validate form data (same validation as save_form)
        if not form_data.get("title"):
            return jsonify({"success": False, "error": "Form title is required"}), 400

        if not form_data.get("questions") or not isinstance(
            form_data["questions"], list
        ):
            return (
                jsonify(
                    {"success": False, "error": "Form must have at least one question"}
                ),
                400,
            )

        # Check for at least one enabled question
        enabled_questions = [
            q for q in form_data["questions"] if q.get("enabled", True)
        ]
        if not enabled_questions:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Form must have at least one enabled question",
                    }
                ),
                400,
            )

        # Prepare update document
        update_document = {
            "title": form_data["title"],
            "questions": form_data["questions"],
            "demographics": form_data.get("demographics", {}),
            "active": form_data.get(
                "active", existing_form.get("active", False)
            ),  # Handle activation
            "last_modified": datetime.utcnow(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # If activating for the first time, generate share URL
        if form_data.get("active") and not existing_form.get("active"):
            update_document["share_url"] = f"https://barmuda.vercel.app/form/{form_id}"
            logger.info(f"Activating survey {form_id} - generated share URL")

        logger.info(
            f"Updating form '{form_data['title']}' (ID: {form_id}) for user {user_id}"
        )

        # Update in Firestore
        form_ref.update(update_document)

        logger.info(f"Form updated successfully: {form_id}")

        # Get final share URL (either existing or newly generated)
        updated_doc = form_ref.get().to_dict()
        share_url = updated_doc.get(
            "share_url", f"https://barmuda.vercel.app/form/{form_id}"
        )

        return (
            jsonify(
                {
                    "success": True,
                    "form_id": form_id,
                    "share_url": share_url,
                    "metadata": {
                        "questions_count": len(form_data["questions"]),
                        "enabled_questions": len(enabled_questions),
                        "demographics_enabled": len(
                            [
                                k
                                for k, v in form_data.get("demographics", {}).items()
                                if v
                            ]
                        ),
                        "updated_at": update_document["updated_at"],
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error updating form {form_id}: {str(e)}")
        return (
            jsonify(
                {"success": False, "error": "Internal server error while updating form"}
            ),
            500,
        )


@app.route("/api/form/<form_id>")
@login_required
def get_form(form_id):
    """Get form data for editing"""
    try:
        user_id = request.user["uid"]

        # Get form from Firestore
        form_ref = db.collection("forms").document(form_id)
        form_doc = form_ref.get()

        if not form_doc.exists:
            return jsonify({"success": False, "error": "Form not found"}), 404

        form_data = form_doc.to_dict()

        # Check if user owns this form
        if form_data.get("creator_id") != user_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        return (
            jsonify(
                {
                    "success": True,
                    "form": {
                        "title": form_data.get("title"),
                        "questions": form_data.get("questions", []),
                        "demographics": form_data.get("demographics", {}),
                    },
                    "metadata": {
                        "form_id": form_id,
                        "created_at": form_data.get("created_at"),
                        "updated_at": form_data.get("updated_at"),
                        "status": form_data.get("status"),
                        "response_count": form_data.get("response_count", 0),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error loading form {form_id}: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/api/health")
def health_check():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "status": "healthy",
                "firebase": True,
                "openai": bool(os.environ.get("OPENAI_API_KEY")),
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
        200,
    )


# Error handlers
@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized access"}), 401


@app.errorhandler(403)
def forbidden(error):
    return jsonify({"error": "Forbidden access"}), 403


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ================================
# MODULE 4: CHAT INTERFACE ROUTES
# ================================

import hashlib
import time

from chat_engine import get_chat_agent


@app.route("/api/form/<form_id>/public")
def get_form_public(form_id):
    """Get public form metadata (title, active status) for widget usage"""
    try:
        # Get form from Firestore
        form_ref = db.collection("forms").document(form_id)
        form_doc = form_ref.get()
        
        if not form_doc.exists:
            return jsonify({"success": False, "error": "Form not found"}), 404
        
        form_data = form_doc.to_dict()
        
        # Return only public metadata needed for widget
        return jsonify({
            "success": True,
            "form": {
                "title": form_data.get("title", "Survey"),
                "active": form_data.get("active", False),
                "form_id": form_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting public form data: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get form data"}), 500


@app.route("/form/<form_id>")
def form_response_page(form_id):
    """Public form response page for respondents"""
    try:
        # Verify form exists
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return (
                render_template(
                    "error.html",
                    error_title="Form Not Found",
                    error_message="This form doesn't exist or has been removed.",
                ),
                404,
            )

        form_data = form_doc.to_dict()

        # Check if form is active - CRITICAL: Only active forms can receive responses
        if not form_data.get("active", False):
            return (
                render_template(
                    "error.html",
                    error_title="Survey Not Available",
                    error_message="This survey is currently paused and not accepting responses.",
                ),
                403,
            )

        return render_template(
            "chat.html",
            form_id=form_id,
            form_title=form_data.get("title", "Survey"),
            form_description=form_data.get("description", ""),
        )

    except Exception as e:
        print(f"Error loading form page: {str(e)}")
        return (
            render_template(
                "error.html",
                error_title="Error Loading Form",
                error_message="There was an error loading this form. Please try again later.",
            ),
            500,
        )


@app.route("/embed/<form_id>")
def embed_form(form_id):
    """Embeddable form chat interface (iframe-optimized)"""
    try:
        # Verify form exists and is active (same validation as regular form)
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return (
                render_template(
                    "error.html",
                    error_title="Form Not Found",
                    error_message="This form doesn't exist or has been removed.",
                ),
                404,
            )

        form_data = form_doc.to_dict()

        # Check if form is active
        if not form_data.get("active", False):
            return (
                render_template(
                    "error.html",
                    error_title="Survey Not Available",
                    error_message="This survey is currently paused and not accepting responses.",
                ),
                403,
            )

        # Create response with CORS headers for embedding
        response = app.make_response(render_template(
            "embed.html",
            form_id=form_id,
            form_title=form_data.get("title", "Survey"),
            form_description=form_data.get("description", ""),
        ))
        
        # Add headers to allow iframe embedding from any domain
        # Remove X-Frame-Options to let CSP handle framing
        response.headers.pop('X-Frame-Options', None)
        response.headers['Content-Security-Policy'] = "frame-ancestors https: http: file:"
        
        return response

    except Exception as e:
        print(f"Error loading embed form: {str(e)}")
        return (
            render_template(
                "error.html",
                error_title="Error Loading Form",
                error_message="There was an error loading this form. Please try again later.",
            ),
            500,
        )


@app.route("/widget.js")
def widget_script():
    """Serve the widget JavaScript file with proper CORS headers"""
    response = send_from_directory('static', 'widget.js', mimetype='application/javascript')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
    return response


@app.route("/api/chat/start", methods=["POST"])
def start_chat_session():
    """Start a new chat session or resume existing one"""
    try:
        data = request.get_json()
        form_id = data.get("form_id")
        device_id = data.get("device_id")  # From FingerprintJS
        location = data.get("location", {})  # Geolocation data

        if not form_id:
            return jsonify({"error": "form_id is required"}), 400

        # CRITICAL: Verify form exists and is active before allowing responses
        try:
            form_doc = db.collection("forms").document(form_id).get()
            if not form_doc.exists:
                return jsonify({"error": "Form not found"}), 404

            form_data = form_doc.to_dict()
            if not form_data.get("active", False):
                return (
                    jsonify(
                        {
                            "error": "Survey not available",
                            "message": "This survey is currently paused and not accepting responses.",
                        }
                    ),
                    403,
                )
        except Exception as e:
            logger.error(f"Error validating form {form_id}: {str(e)}")
            return jsonify({"error": "Error validating form"}), 500

        # Check for existing session by device_id + form_id
        existing_session = None
        if device_id:
            try:
                print(
                    f"Looking for existing session with device_id: {device_id}, form_id: {form_id}"
                )

                # Query Firestore for existing sessions with this device_id and form_id
                sessions_ref = db.collection("chat_sessions")

                # First, let's check all sessions for this device_id
                all_device_sessions = list(
                    sessions_ref.where(filter=FieldFilter("metadata.device_id", "==", device_id)).stream()
                )
                print(
                    f"Total sessions for device {device_id}: {len(all_device_sessions)}"
                )

                # Debug: List all sessions in the collection
                all_sessions = list(sessions_ref.limit(5).stream())
                print(f"\nDEBUG: First 5 sessions in collection:")
                for sess in all_sessions:
                    sess_data = sess.to_dict()
                    print(f"  - ID: {sess.id}")
                    print(
                        f"    Device ID: {sess_data.get('metadata', {}).get('device_id')}"
                    )
                    print(f"    Form ID: {sess_data.get('form_id')}")
                    print(f"    Ended: {sess_data.get('metadata', {}).get('ended')}")

                # Simplified query to avoid index requirement
                # First get all sessions for this device and form
                query = sessions_ref.where(
                    filter=FieldFilter("metadata.device_id", "==", device_id)
                ).where(
                    filter=FieldFilter("form_id", "==", form_id)
                )

                # Get all matching sessions
                all_matching = list(query.stream())

                # Sort by start time (newest first)
                all_matching.sort(
                    key=lambda s: s.to_dict().get("metadata", {}).get("start_time", ""),
                    reverse=True,
                )

                # Get most recent session (ended or not)
                existing_sessions = all_matching[:1] if all_matching else []
                print(f"Found {len(all_matching)} total sessions")

                if existing_sessions:
                    existing_session = existing_sessions[0]
                    print(f"Found existing session: {existing_session.id}")
                    session_data = existing_session.to_dict()
                    print(
                        f"Session device_id: {session_data.get('metadata', {}).get('device_id')}"
                    )
                    print(f"Session form_id: {session_data.get('form_id')}")
                    print(
                        f"Session ended: {session_data.get('metadata', {}).get('ended')}"
                    )
                else:
                    print("No existing sessions found")
            except Exception as e:
                print(f"Error checking for existing sessions: {e}")
                import traceback

                traceback.print_exc()

        # If existing session found, check if it's ended
        if existing_session:
            session_id = existing_session.id
            session_data = existing_session.to_dict()
            is_ended = session_data.get("metadata", {}).get("ended", False)

            # If session is ended, return the ended state
            if is_ended:
                return jsonify(
                    {
                        "session_id": session_id,
                        "greeting": "This form has already been completed. Thank you! 🎉",
                        "chat_history": session_data.get("chat_history", []),
                        "resumed": False,
                        "ended": True,
                        "success": True,
                    }
                )
            else:
                # Resume active session - let agent generate natural resumption response
                agent = get_chat_agent()
                try:
                    greeting_result = agent.process_message(
                        session_id, "Hello, I'm back to continue our conversation!"
                    )
                    greeting_message = greeting_result.get(
                        "response", "Great to have you back! Let's continue our conversation. 😊"
                    )
                except Exception as e:
                    print(f"Error getting resumption greeting: {e}")
                    greeting_message = "Great to have you back! Let's continue our conversation. 😊"
                
                return jsonify(
                    {
                        "session_id": session_id,
                        "greeting": greeting_message,
                        "chat_history": session_data.get("chat_history", []),
                        "resumed": True,
                        "ended": False,
                        "success": True,
                    }
                )

        # Create new session using chat agent
        try:
            agent = get_chat_agent()
            session_id = agent.create_session(form_id, device_id, location)
        except Exception as e:
            logger.error(f"Failed to create chat agent or session: {str(e)}")
            return jsonify({"error": f"Chat initialization failed: {str(e)}"}), 500

        # Get initial greeting
        try:
            greeting_result = agent.process_message(
                session_id, "Hello, I'm ready to start!"
            )
            greeting_message = greeting_result.get(
                "response", "Hello! Ready to get started? 😊"
            )
        except Exception as e:
            print(f"Error getting initial greeting: {e}")
            greeting_message = "Hello! Welcome to the survey. Let's get started! 😊"

        return jsonify(
            {
                "session_id": session_id,
                "greeting": greeting_message,
                "resumed": False,
                "success": True,
            }
        )

    except Exception as e:
        print(f"Error starting chat session: {str(e)}")
        return jsonify({"error": "Failed to start chat session"}), 500



@app.route("/api/chat/message", methods=["POST"])
def process_chat_message():
    """Process a chat message"""
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        message = data.get("message", "").strip()

        if not session_id or not message:
            return jsonify({"error": "session_id and message are required"}), 400

        # Rate limiting check
        if not check_rate_limit(session_id, request.remote_addr):
            return jsonify({"error": "Rate limit exceeded. Please slow down."}), 429

        # Process message with GPT-powered agent
        agent = get_chat_agent()
        result = agent.process_message(session_id, message)

        if not result.get("success"):
            return (
                jsonify(
                    {
                        "response": result.get(
                            "response",
                            "Sorry, I had trouble processing that. Could you try again? 😅",
                        ),
                        "error": result.get("error"),
                        "success": False,
                    }
                ),
                200,
            )

        # Check if conversation ended
        conversation_ended = result.get("metadata", {}).get("ended", False)

        response_data = {
            "response": result["response"],
            "success": True,
            "session_updated": result.get("session_updated", False),
            "ended": conversation_ended,
        }

        # If ended, trigger data extraction
        if conversation_ended:
            try:
                extraction_result = extract_chat_responses(session_id)
                response_data["extraction_triggered"] = True
                response_data["extraction_success"] = extraction_result.get(
                    "success", False
                )
            except Exception as e:
                print(f"Extraction error: {str(e)}")
                response_data["extraction_triggered"] = False

        return jsonify(response_data)

    except Exception as e:
        # Enhanced error logging for debugging
        import traceback
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "request_data": data if 'data' in locals() else None,
            "message": data.get('message') if 'data' in locals() and data else None
        }
        print(f"🚨 CHAT MESSAGE ERROR: {error_details}")
        
        # Also log to file for debugging
        with open('/tmp/flask_errors.log', 'a') as f:
            from datetime import datetime
            f.write(f"{datetime.now()}: {error_details}\n")
        
        return (
            jsonify(
                {
                    "response": "I apologize, but I encountered an error. Could you try sending your message again? 🤔",
                    "success": False,
                    "error": "Internal processing error",
                }
            ),
            500,
        )


@app.route("/api/chat/status/<session_id>")
def get_chat_status(session_id):
    """Get chat session status"""
    try:
        from chat_engine import load_session

        chat_session = load_session(session_id)

        total_questions = len(
            [
                q
                for q in chat_session.form_data.get("questions", [])
                if q.get("enabled", True)
            ]
        )
        answered_questions = len(
            [r for r in chat_session.responses.values() if r.get("value") != "[SKIP]"]
        )

        # Debug logging
        print(f"Progress Debug - Session: {session_id}")
        print(f"  Total questions: {total_questions}")
        print(f"  Responses count: {len(chat_session.responses)}")
        print(f"  Answered questions: {answered_questions}")
        print(f"  Current question index: {chat_session.current_question_index}")
        print(f"  Session responses: {chat_session.responses}")

        progress_percentage = int((answered_questions / max(total_questions, 1)) * 100)
        print(f"  Calculated progress: {progress_percentage}%")

        return jsonify(
            {
                "session_id": session_id,
                "progress": {
                    "current_question": chat_session.current_question_index,
                    "total_questions": total_questions,
                    "answered_questions": answered_questions,
                    "percentage": progress_percentage,
                    "responses_debug": chat_session.responses,  # Debug info
                },
                "metadata": chat_session.metadata,
                "ended": chat_session.metadata.get("ended", False),
            }
        )

    except Exception as e:
        print(f"Error getting chat status: {str(e)}")
        return jsonify({"error": "Session not found"}), 404


# Rate limiting helper
chat_rate_limits = {}


def check_rate_limit(session_id, ip_address):
    """Check if request is within rate limits"""
    current_time = time.time()
    key = f"{session_id}_{ip_address}"

    if key not in chat_rate_limits:
        chat_rate_limits[key] = []

    # Clean old entries (older than 1 hour)
    chat_rate_limits[key] = [
        t for t in chat_rate_limits[key] if current_time - t < 3600
    ]

    # Check if under limit (50 messages per hour)
    if len(chat_rate_limits[key]) >= 50:
        return False

    # Add current request
    chat_rate_limits[key].append(current_time)
    return True


# Import the data extraction function
from data_extraction import extract_chat_responses

# ================================
# MODULE 6: RESPONSE VIEWING ROUTES
# ================================


@app.route("/api/responses/<form_id>")
@login_required
def get_form_responses(form_id):
    """Get all responses for a form"""
    try:
        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return jsonify({"error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 403

        # Get responses
        responses_query = (
            db.collection("responses").where(filter=FieldFilter("form_id", "==", form_id)).stream()
        )
        responses = []

        for response_doc in responses_query:
            response_data = response_doc.to_dict()
            # Handle created_at field - might be datetime object or string
            created_at = response_data.get("created_at")
            if created_at:
                if hasattr(created_at, "isoformat"):
                    created_at = created_at.isoformat()
                # If it's already a string, keep it as is

            responses.append(
                {
                    "id": response_doc.id,
                    "responses": response_data.get("responses", {}),
                    "metadata": response_data.get("metadata", {}),
                    "created_at": created_at,
                    "partial": response_data.get("partial", False),
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
        print(f"Error getting responses: {str(e)}")
        return jsonify({"error": "Failed to fetch responses"}), 500


@app.route("/api/wordcloud/<form_id>/<int:question_index>")
@login_required
def generate_wordcloud(form_id, question_index):
    """Generate word cloud data for text questions"""
    try:
        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return jsonify({"error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 403

        # Get responses for this question
        responses_query = (
            db.collection("responses").where(filter=FieldFilter("form_id", "==", form_id)).stream()
        )
        text_responses = []

        for response_doc in responses_query:
            response_data = response_doc.to_dict()
            if "responses" in response_data:
                answer = response_data["responses"].get(str(question_index))
                if answer and answer.get("value") and answer.get("value") != "[SKIP]":
                    text_responses.append(answer.get("value"))

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


def generate_word_frequency_backend(text_responses):
    """Generate word frequency data on the backend"""
    import re
    from collections import Counter

    # Common stop words
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "her",
        "its",
        "our",
        "their",
        "this",
        "that",
        "these",
        "those",
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


@app.route("/responses/<form_id>")
@login_required
def view_form_responses(form_id):
    """View responses for a form"""
    try:
        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return (
                render_template(
                    "error.html",
                    error_title="Form Not Found",
                    error_message="This form doesn't exist or has been removed.",
                ),
                404,
            )

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != session.get("user_id"):
            return (
                render_template(
                    "error.html",
                    error_title="Access Denied",
                    error_message="You don't have permission to view this form's responses.",
                ),
                403,
            )

        return render_template(
            "responses.html",
            form_id=form_id,
            form_title=form_data.get("title", "Untitled Form"),
            questions=form_data.get("questions", []),
        )

    except Exception as e:
        print(f"Error loading responses page: {str(e)}")
        return (
            render_template(
                "error.html",
                error_title="Error Loading Responses",
                error_message="There was an error loading the responses. Please try again later.",
            ),
            500,
        )


@app.route("/api/export/<form_id>/<format>")
@login_required
def export_responses(form_id, format):
    """Export responses in JSON or CSV format"""
    try:
        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return jsonify({"error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 403

        # Get responses
        responses_query = (
            db.collection("responses").where(filter=FieldFilter("form_id", "==", form_id)).stream()
        )
        responses = []

        for response_doc in responses_query:
            response_data = response_doc.to_dict()
            responses.append(response_data)

        if format.lower() == "json":
            from flask import Response

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
                for response in responses:
                    if "responses" in response:
                        for key, value in response["responses"].items():
                            fieldnames.add(
                                f"Q{int(key)+1}: {value.get('question_text', f'Question {key}')}"
                            )
                    fieldnames.update(
                        ["Response ID", "Created At", "Partial", "Device ID"]
                    )

                fieldnames = sorted(list(fieldnames))
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()

                for response in responses:
                    row = {
                        "Response ID": response.get("session_id", ""),
                        "Created At": str(response.get("created_at", "")),
                        "Partial": response.get("partial", False),
                        "Device ID": response.get("metadata", {}).get("device_id", ""),
                    }

                    # Add question responses
                    if "responses" in response:
                        for key, value in response["responses"].items():
                            field_name = f"Q{int(key)+1}: {value.get('question_text', f'Question {key}')}"
                            row[field_name] = value.get("value", "")

                    writer.writerow(row)

            from flask import Response

            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=responses_{form_id}.csv"
                },
            )

        else:
            return jsonify({"error": "Invalid format. Use json or csv"}), 400

    except Exception as e:
        print(f"Error exporting responses: {str(e)}")
        return jsonify({"error": "Failed to export responses"}), 500


@app.route("/api/forms/<form_id>/status", methods=["PUT"])
@login_required
def update_form_status(form_id):
    """Toggle form active/inactive status"""
    try:
        data = request.get_json()
        if not data or "status" not in data:
            return jsonify({"error": "Status is required"}), 400

        new_status = data["status"]
        if new_status not in ["active", "inactive"]:
            return jsonify({"error": "Status must be active or inactive"}), 400

        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return jsonify({"error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 403

        # Update active status (convert string to boolean)
        is_active = new_status == "active"
        db.collection("forms").document(form_id).update(
            {"active": is_active, "updated_at": datetime.now().isoformat()}
        )

        return jsonify({"success": True, "status": new_status})

    except Exception as e:
        logger.error(f"Error updating form status: {str(e)}")
        return jsonify({"error": "Failed to update form status"}), 500


@app.route("/api/forms/<form_id>", methods=["DELETE"])
@login_required
def delete_form(form_id):
    """Delete a form and all its responses"""
    try:
        from flask import session  # Explicit import to avoid F823 error

        # Verify form ownership
        form_doc = db.collection("forms").document(form_id).get()
        if not form_doc.exists:
            return jsonify({"error": "Form not found"}), 404

        form_data = form_doc.to_dict()
        if form_data.get("creator_id") != session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 403

        # Delete form
        db.collection("forms").document(form_id).delete()

        # Delete associated responses (optional - you might want to keep them)
        responses_ref = db.collection("responses").where(filter=FieldFilter("form_id", "==", form_id))
        responses = responses_ref.stream()

        for response in responses:
            response.reference.delete()

        # Delete chat sessions
        sessions_ref = db.collection("chat_sessions").where(filter=FieldFilter("form_id", "==", form_id))
        sessions = sessions_ref.stream()

        for session in sessions:
            session.reference.delete()

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Error deleting form: {str(e)}")
        return jsonify({"error": "Failed to delete form"}), 500



@app.route("/api/test/extraction/<session_id>")
def test_extraction_endpoint(session_id):
    """Test endpoint to check extraction data for a session"""
    try:
        # Check chat_responses collection first
        response_doc = db.collection("chat_responses").document(session_id).get()
        
        if response_doc.exists:
            response_data = response_doc.to_dict()
            form_data = response_data.get("form_data", {})
            
            return jsonify({
                "session_id": session_id,
                "form_title": form_data.get("title", "Unknown Form"),
                "responses": response_data.get("responses", {}),
                "chat_history": response_data.get("chat_history", []),
                "metadata": response_data.get("metadata", {}),
                "extraction_found": True
            })
        
        # If not in chat_responses, check chat_sessions
        session_doc = db.collection("chat_sessions").document(session_id).get()
        
        if session_doc.exists:
            session_data = session_doc.to_dict()
            form_data = session_data.get("form_data", {})
            
            return jsonify({
                "session_id": session_id,
                "form_title": form_data.get("title", "Unknown Form"),
                "responses": session_data.get("responses", {}),
                "chat_history": session_data.get("chat_history", []),
                "metadata": session_data.get("metadata", {}),
                "extraction_found": True,
                "note": "Found in chat_sessions (may not be ended yet)"
            })
        
        return jsonify({
            "error": "Session not found",
            "session_id": session_id,
            "extraction_found": False
        }), 404
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve extraction data: {str(e)}",
            "session_id": session_id,
            "extraction_found": False
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
