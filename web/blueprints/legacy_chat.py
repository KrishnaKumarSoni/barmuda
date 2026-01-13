import logging
import os
import asyncio
from datetime import datetime
from flask import Blueprint, jsonify, request, Response, stream_with_context
from web.utils.auth import require_conversation_limit
from web.services.chat_adapter import process_chat_message, ChatAdapter
from web.config import Config
from web.extensions import db

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
        input_session_id = data.get("session_id")
        
        if not form_id:
            return jsonify({"success": False, "error": "form_id is required"}), 400
            
        # Attempt to resume if session_id is provided
        if input_session_id:
            print(f"DEBUG: Attempting to resume session: {input_session_id}")
            result = asyncio.run(ChatAdapter.get_current_state(input_session_id))
            print(f"DEBUG: Resume result: {result.get('success')}, Error: {result.get('error')}")
            
            if result.get("success"):
                print("DEBUG: Session resumed successfully.")
                return jsonify({
                    "success": True,
                    "session_id": input_session_id,
                    "resumed": True,
                    "chat_history": result.get("history", []),
                    "chip_options": result.get("chip_options"),
                    "greeting": "" 
                })

        print("DEBUG: Resumption failed or no session ID. Generating new session.")
        # Generate session ID similar to legacy format
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        print(f"DEBUG: New Session ID: {session_id}")

        # IMMEDIATELY persist session to DB to ensure future lookups work
        # even if the agent processing takes time or fails.
        try:
            db.collection("sessions").document(session_id).set({
                "session_id": session_id,
                "form_id": form_id,
                "session_state": "ONGOING",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }, merge=True)
            print(f"DEBUG: Persisted session {session_id} to Firestore.")
        except Exception as db_err:
            logger.error(f"Failed to persist initial session: {db_err}")
            # Continue anyway, aiming for agent-side persistence as backup
        
        # Bootstrap the session using the new agent
        # "START_SURVEY_SESSION" is a trigger message for the agent to load the survey
        result = process_chat_message(session_id, form_id, "START_SURVEY_SESSION")
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "session_id": session_id,
                "greeting": result.get("response"), # For backward compatibility if needed, though widget mostly relies on subsequent messages
                "chip_options": result.get("chip_options"),
                "ended": result.get("ended", False)
            })
        else:
             return jsonify(result), 500

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
            
        # Call the new agent adapter
        # It handles form_id lookup if not provided
        result = process_chat_message(session_id, None, message)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@legacy_chat_bp.route("/api/chat/status/<session_id>")
def get_chat_status(session_id):
    try:
        # Use asyncio.run for the async get_current_state method
        result = asyncio.run(ChatAdapter.get_current_state(session_id))
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "status": result.get("metadata", {})
            })
        return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@legacy_chat_bp.route("/api/chat/check_chips", methods=["POST"])
def check_chips():
    """Check if a message should have chip options"""
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        
        if not session_id:
            return jsonify({"success": False, "error": "Missing session_id"}), 400

        # Retrieve current state from the new agent
        result = asyncio.run(ChatAdapter.get_current_state(session_id))
        
        if result.get("success"):
             return jsonify({
                "success": True, 
                "chip_options": result.get("chip_options", {"show_chips": False})
            })

        return jsonify({"success": False, "error": result.get("error")}), 404

    except Exception as e:
        logger.error(f"Error checking chips: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def sync_stream_generator(session_id, form_id, message):
    """
    Bridge async generator to synchronous iterator for Flask streaming.
    Runs a temporary event loop to consume the async stream.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    agen = ChatAdapter.stream_message_async(session_id, form_id, message)
    
    try:
        while True:
            try:
                chunk = loop.run_until_complete(agen.__anext__())
                yield chunk
            except StopAsyncIteration:
                break
    finally:
        loop.close()

@legacy_chat_bp.route("/api/chat/stream", methods=["POST"])
def stream_chat():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        message = data.get("message")
        form_id = data.get("form_id") # Optional, adapter looks it up
        
        if not session_id or not message:
            return jsonify({"success": False, "error": "session_id and message are required"}), 400

        return Response(
            stream_with_context(sync_stream_generator(session_id, form_id, message)),
            mimetype='text/event-stream'
        )
    except Exception as e:
        logger.error(f"Error streaming chat: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500