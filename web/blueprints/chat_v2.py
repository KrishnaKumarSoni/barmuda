import logging
from flask import Blueprint, request, jsonify
from web.services.chat_adapter import process_chat_message
from web.utils.auth import require_conversation_limit

logger = logging.getLogger(__name__)

chat_v2_bp = Blueprint('chat_v2', __name__)

@chat_v2_bp.route("/api/v2/chat/start", methods=["POST"])
@require_conversation_limit
def start_chat_v2():
    """
    Initializes or resumes a LangGraph session.
    Returns the initial greeting or chat history.
    """
    try:
        data = request.get_json()
        form_id = data.get("form_id")
        session_id = data.get("session_id") # Unique ID from device/frontend
        
        if not form_id or not session_id:
            return jsonify({"success": False, "error": "form_id and session_id are required"}), 400

        # Sending a specialized trigger message to bootstrap the session
        # The agent middleware 'bootstrap_session_middleware' will detect 
        # empty responses and load the survey regardless of input.
        result = process_chat_message(session_id, form_id, "START_SURVEY_SESSION")
        
        # Format for frontend compatibility
        if result.get("success"):
            return jsonify({
                "success": True,
                "session_id": session_id,
                "greeting": result.get("response"), # Match frontend expected 'greeting' field
                "chip_options": result.get("chip_options"),
                "ended": result.get("ended", False)
            })
        
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error starting V2 chat: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@chat_v2_bp.route("/api/v2/chat/message", methods=["POST"])
def send_message_v2():
    """
    Processes a user message through the LangGraph agent.
    """
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        form_id = data.get("form_id")
        message = data.get("message")
        
        if not session_id or not form_id or not message:
            return jsonify({"success": False, "error": "session_id, form_id and message are required"}), 400
            
        result = process_chat_message(session_id, form_id, message)
        
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error processing V2 message: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
