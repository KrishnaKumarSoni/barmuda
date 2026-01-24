import logging
import os
import asyncio
import threading
import time
from datetime import datetime
from flask import Blueprint, jsonify, request, Response, stream_with_context
from web.utils.auth import require_conversation_limit
from web.services.chat_adapter import process_chat_message, ChatAdapter
from web.config import Config
from web.extensions import db

logger = logging.getLogger(__name__)

legacy_chat_bp = Blueprint('legacy_chat', __name__)

def background_session_write(session_id, form_id):
    """Background task to write session to Firestore"""
    start = time.time()
    try:
        db.collection("sessions_v2").document(session_id).set({
            "session_id": session_id,
            "form_id": form_id,
            "session_state": "ONGOING",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }, merge=True)
        print(f"DEBUG: Persisted session {session_id} to Firestore (background). Took {time.time()-start:.4f}s")
    except Exception as db_err:
        logger.error(f"Failed to persist initial session: {db_err}")

@legacy_chat_bp.route("/api/chat/start", methods=["POST"])
@require_conversation_limit
def start_chat():
    start_time = time.time()
    print(f"DEBUG: start_chat entry at {start_time}")
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
            t0 = time.time()
            result = asyncio.run(ChatAdapter.get_current_state(input_session_id))
            print(f"DEBUG: Resume get_current_state took {time.time()-t0:.4f}s")
            
            if result.get("success"):
                print(f"DEBUG: Session resumed successfully. Total time {time.time()-start_time:.4f}s")
                return jsonify({
                    "success": True,
                    "session_id": input_session_id,
                    "resumed": True,
                    "chat_history": result.get("history", []),
                    "chip_options": result.get("chip_options"),
                    "greeting": "" 
                })

        print("DEBUG: Resumption failed or no session ID. Generating new session.")
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        # IMMEDIATELY persist session to DB to ensure future lookups work
        # Moved to background thread to avoid blocking the request
        threading.Thread(target=background_session_write, args=(session_id, form_id)).start()
        
        # Bootstrap the session using the new agent
        print("DEBUG: Calling process_chat_message...")
        t1 = time.time()
        result = process_chat_message(session_id, form_id, "START_SURVEY_SESSION")
        print(f"DEBUG: process_chat_message took {time.time()-t1:.4f}s")
        
        if result.get("success"):
            print(f"DEBUG: start_chat success. Total time {time.time()-start_time:.4f}s")
            return jsonify({
                "success": True,
                "session_id": session_id,
                "greeting": result.get("response"), 
                "chip_options": result.get("chip_options"),
                "ended": result.get("ended", False)
            })
        else:
             return jsonify(result), 500

    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}")
        print(f"DEBUG: start_chat error {str(e)}. Total time {time.time()-start_time:.4f}s")
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
    start = time.time()
    print(f"DEBUG: get_chat_status entry for {session_id} at {start}")
    try:
        # Use asyncio.run for the async get_current_state method
        result = asyncio.run(ChatAdapter.get_current_state(session_id))
        print(f"DEBUG: get_current_state took {time.time()-start:.4f}s")
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "status": result.get("metadata", {})
            })
        return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 404
    except Exception as e:
        print(f"DEBUG: get_chat_status error {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def sync_stream_generator(session_id, form_id, message):
    """
    Bridge async generator to synchronous iterator for Flask streaming.
    Runs a temporary event loop to consume the async stream.
    """
    # Attempt to recover form_id from Firestore if missing (Crucial for stateless backends)
    if not form_id:
        try:
            print(f"DEBUG: Recovering form_id for session {session_id}")
            doc = db.collection("sessions_v2").document(session_id).get()
            if doc.exists:
                form_id = doc.to_dict().get("form_id")
                print(f"DEBUG: Recovered form_id: {form_id}")
            else:
                print(f"DEBUG: Session document not found for {session_id}")
        except Exception as e:
            logger.error(f"Failed to recover form_id: {e}")

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
