import logging
from flask import Blueprint, jsonify, request
from web.utils.auth import require_conversation_limit
from chat_engine import get_chat_agent, load_session
from web.config import Config

logger = logging.getLogger(__name__)

legacy_chat_bp = Blueprint('legacy_chat', __name__)

@legacy_chat_bp.route("/api/chat/start", methods=["POST"])
@require_conversation_limit
def start_chat():
    try:
        data = request.get_json()
        form_id = data.get("form_id")
        device_id = data.get("device_id")
        location = data.get("location")
        
        if not form_id:
            return jsonify({"success": False, "error": "form_id is required"}), 400
            
        agent = get_chat_agent()
        session_id = agent.create_session(form_id, device_id, location)
        
        return jsonify({
            "success": True,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@legacy_chat_bp.route("/api/chat/message", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        message = data.get("message")
        
        if not session_id or not message:
            return jsonify({"success": False, "error": "session_id and message are required"}), 400
            
        agent = get_chat_agent()
        result = agent.process_message(session_id, message)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@legacy_chat_bp.route("/api/chat/status/<session_id>")
def get_chat_status(session_id):
    try:
        session = load_session(session_id)
        return jsonify({
            "success": True,
            "status": session.metadata
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 404

@legacy_chat_bp.route("/api/chat/check_chips", methods=["POST"])
def check_chips():
    """Check if a message should have chip options"""
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        message = data.get("message")

        if not session_id or not message:
            return jsonify({"success": False, "error": "Missing session_id or message"}), 400

        # Import dynamically to avoid circular imports if any, or just use global
        if Config.USE_GROQ:
            from groq_chat_engine import _get_natural_question_data, load_session
        else:
            from chat_engine import _get_natural_question_data, load_session

        try:
            session = load_session(session_id)
        except Exception as e:
            return jsonify({"success": False, "error": f"Session not found: {str(e)}"}), 404

        questions = session.form_data.get("questions", [])
        current_q_idx = session.current_question_index

        if current_q_idx >= len(questions):
            return jsonify({"success": True, "chip_options": {"show_chips": False}})

        current_q = questions[current_q_idx]

        if not current_q.get("enabled", True):
            return jsonify({"success": True, "chip_options": {"show_chips": False}})

        if str(current_q_idx) in session.responses:
            return jsonify({"success": True, "chip_options": {"show_chips": False}})

        # Determine chips logic
        q_type = current_q.get("type", "text")
        q_text = current_q.get("text", "")
        
        natural_q_data = _get_natural_question_data(session_id, q_text, q_type, current_q_idx)
        
        if natural_q_data.get("show_chips"):
            return jsonify({
                "success": True, 
                "chip_options": {
                    "show_chips": True,
                    "chip_type": natural_q_data.get("chip_type"),
                    "options": natural_q_data.get("chip_options", [])
                }
            })
            
        return jsonify({"success": True, "chip_options": {"show_chips": False}})

    except Exception as e:
        logger.error(f"Error checking chips: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
