import os
import requests
import logging
import json
import asyncio
from typing import Dict, Any, Optional, AsyncIterator

logger = logging.getLogger(__name__)

# This env var should be set in Vercel/Local .env
# Default to your deployed URL for convenience, but env var overrides it
DEFAULT_AGENT_URL = "https://barmuda-agent-230172906866.asia-south1.run.app"
AGENT_URL = os.environ.get("AGENT_SERVICE_URL", DEFAULT_AGENT_URL)

class ChatAdapter:
    """
    Bridge between Flask and the Remote Agent Service on Cloud Run.
    Sends HTTP requests instead of running LangGraph locally.
    """

    @classmethod
    async def process_message_async(cls, session_id: str, form_id: str, message: str) -> Dict[str, Any]:
        """
        Sends chat message to the remote Agent Service.
        """
        if not AGENT_URL:
            logger.error("AGENT_SERVICE_URL is not set.")
            return {"success": False, "error": "Configuration error: Agent URL missing."}

        try:
            payload = {
                "session_id": session_id, 
                "form_id": form_id, 
                "message": message
            }
            
            # Using requests (synchronous) within async wrapper for simplicity
            # In a high-load async app, use aiohttp/httpx
            # Running in executor to avoid blocking async loop if called from async context
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(f"{AGENT_URL}/chat", json=payload, timeout=60))
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Agent Service returned {response.status_code}: {response.text}")
                return {
                    "success": False, 
                    "error": f"Agent error ({response.status_code})",
                    "response": "I'm having trouble reaching my brain right now."
                }

        except Exception as e:
            logger.error(f"Failed to connect to Agent Service: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "response": "Connection error. Please try again."
            }

    @classmethod
    async def get_current_state(cls, session_id: str) -> Dict[str, Any]:
        """
        Fetches current state from the remote Agent Service.
        """
        if not AGENT_URL:
            return {"success": False, "error": "AGENT_SERVICE_URL missing"}

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(
                f"{AGENT_URL}/state", 
                json={"session_id": session_id},
                timeout=10
            ))
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Status {response.status_code}"}

        except Exception as e:
            logger.error(f"State fetch error: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def stream_message_async(cls, session_id: str, form_id: str, message: str) -> AsyncIterator[str]:
        """
        Streaming is not yet fully implemented over the HTTP bridge in this version.
        Falls back to standard non-streaming response.
        """
        # For true streaming, you'd need to consume the remote stream response.
        # For now, we yield the final result as a single chunk to maintain interface compatibility.
        result = await cls.process_message_async(session_id, form_id, message)
        
        if result.get("success"):
            # Yield as if it were a stream token
            yield f"data: {json.dumps({'type': 'token', 'text': result.get('response', '')})}\n\n"
            
            # Yield metadata
            metadata = {
                "type": "meta",
                "chip_options": result.get("chip_options"),
                "ended": result.get("ended"),
                "session_id": session_id
            }
            yield f"data: {json.dumps(metadata)}\n\n"
        else:
             yield f"data: {json.dumps({'type': 'error', 'message': result.get('error')})}\n\n"


def process_chat_message(session_id: str, form_id: str, message: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for Flask routes.
    """
    # Simply call the API synchronously
    if not AGENT_URL:
        return {"success": False, "error": "AGENT_SERVICE_URL not configured"}

    try:
        payload = {"session_id": session_id, "form_id": form_id, "message": message}
        response = requests.post(f"{AGENT_URL}/chat", json=payload, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Sync Chat Process Error: {e}")
        return {"success": False, "error": str(e)}
