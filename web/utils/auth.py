from functools import wraps
import logging
from flask import session, jsonify, redirect, request
from billing import get_subscription_manager

logger = logging.getLogger(__name__)

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

def require_form_creation(f):
    """Decorator to check if user can create forms"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, "user"):
            return jsonify({"error": "Authentication required"}), 401

        try:
            subscription_manager = get_subscription_manager()
            can_create, error_message = subscription_manager.can_create_form(
                request.user["uid"]
            )

            if not can_create:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": error_message,
                            "upgrade_required": True,
                            "feature": "form_creation",
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error checking form creation limits: {str(e)}")
            # Allow on error to avoid breaking functionality
            return f(*args, **kwargs)

    return decorated_function

def require_conversation_limit(f):
    """Decorator to check conversation limits"""
    from web.extensions import db

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For conversation endpoints, we need to check the form owner, not the respondent
        data = request.get_json() if request.is_json else {}
        form_id = data.get("form_id") or kwargs.get("form_id")

        if not form_id:
            return f(*args, **kwargs)

        try:
            # Get form owner
            form_doc = db.collection("forms").document(form_id).get()
            if not form_doc.exists:
                return jsonify({"error": "Form not found"}), 404

            form_data = form_doc.to_dict()
            form_owner_id = form_data.get("creator_id")

            if not form_owner_id:
                return f(*args, **kwargs)

            subscription_manager = get_subscription_manager()
            can_start, error_message = subscription_manager.can_start_conversation(
                form_owner_id
            )

            if not can_start:
                return (
                    jsonify(
                        {
                            "error": "Conversation limit reached",
                            "message": "This survey has reached its monthly conversation limit. The survey owner needs to upgrade their plan.",
                            "upgrade_required": True,
                        }
                    ),
                    403,
                )

            # If allowed, increment counter and proceed
            subscription_manager.increment_conversation_count(form_owner_id)
            return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error checking conversation limits: {str(e)}")
            # Allow on error to avoid breaking functionality
            return f(*args, **kwargs)

    return decorated_function
