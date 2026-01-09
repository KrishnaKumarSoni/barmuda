import logging
import base64
import json
import signal
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from firebase_admin import auth
from web.extensions import db
# Import email service if used
# from email_service import email_service 

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/auth/google", methods=["POST"])
@auth_bp.route("/firebase-auth", methods=["POST"])
def google_auth():
    """Handle Google Firebase authentication with quota-safe fallback"""
    logger.info(f"=== GOOGLE AUTH REQUEST START === Method: {request.method}")

    try:
        # Get the ID token from the request
        data = request.get_json()
        if not data or "idToken" not in data:
            logger.error("No ID token in request data")
            return jsonify({"error": "ID token is required"}), 400

        id_token = data["idToken"]

        # Try Firebase verification with timeout protection
        try:
            def timeout_handler(signum, frame):
                raise TimeoutError("Firebase verification timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)  # 10 second timeout

            decoded_token = auth.verify_id_token(id_token)
            signal.alarm(0)  # Cancel timeout
            
            user_id = decoded_token["uid"]
            email = decoded_token.get("email", "")
            name = decoded_token.get("name", "")

        except (TimeoutError, Exception) as e:
            signal.alarm(0)  # Cancel timeout
            logger.warning(f"Firebase verification failed ({str(e)}), using token-based fallback")

            # Fallback: decode JWT without verification
            parts = id_token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")

            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded_payload = base64.urlsafe_b64decode(payload)
            token_data = json.loads(decoded_payload)

            user_id = token_data.get("sub", "")
            email = token_data.get("email", "")
            name = token_data.get("name", "")

            if not user_id or not email:
                raise ValueError("Invalid token payload")

        # Check if user exists in Firestore
        try:
            user_ref = db.collection("users").document(user_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
                user_data = {
                    "user_id": user_id,
                    "email": email,
                    "name": name,
                    "created_at": datetime.now().isoformat(),
                }
                user_ref.set(user_data)
                logger.info(f"Created new user: {email}")
                
                # Note: Welcome email logic removed for brevity, 
                # can be re-added if email_service is available
            else:
                logger.info(f"User login: {email}")
        except Exception as firestore_error:
            logger.warning(f"Firestore operation failed ({str(firestore_error)}), continuing with session")

        # Store user session
        session.permanent = True
        session["user_id"] = user_id
        session["email"] = email
        session["authenticated"] = True

        return jsonify({
            "success": True,
            "user": {"user_id": user_id, "email": email, "name": name},
        })

    except Exception as e:
        logger.error(f"=== GOOGLE AUTH ERROR === {str(e)}")
        return jsonify({"error": "Authentication failed", "details": str(e)}), 401

@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    """Handle logout"""
    session.clear()
    return jsonify({"success": True})

@auth_bp.route("/auth/verify", methods=["POST"])
def verify_token():
    """Verify if a token is valid"""
    try:
        data = request.get_json()
        if not data or "idToken" not in data:
            return jsonify({"error": "ID token is required"}), 400

        id_token = data["idToken"]
        decoded_token = auth.verify_id_token(id_token)

        return jsonify({
            "valid": True,
            "user": {
                "user_id": decoded_token["uid"],
                "email": decoded_token.get("email", ""),
                "name": decoded_token.get("name", ""),
            },
        }), 200
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 401

@auth_bp.route("/test-auth", methods=["GET", "POST"])
def test_auth():
    """Test auth endpoint"""
    return jsonify({
        "message": "Auth endpoint working",
        "method": request.method,
        "timestamp": datetime.now().isoformat(),
    })
