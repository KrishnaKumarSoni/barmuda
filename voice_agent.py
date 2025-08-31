import logging
import os
from typing import Dict, Optional

import requests

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_API_BASE = os.environ.get("ELEVENLABS_API_BASE", "https://api.elevenlabs.io")


def _headers() -> Dict[str, str]:
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not configured")
    return {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }


def create_conversational_agent(voice_id: str, language: str = "en", form_title: str = "Survey") -> Dict:
    """Create a conversational AI agent for a form using the specified voice_id.
    
    Args:
        voice_id: The ElevenLabs voice ID to use for the agent
        language: Language code (e.g., 'en', 'hi') 
        form_title: Title of the form for context
        
    Returns:
        Dict with agent_id if successful, or error information
    """
    if not ELEVENLABS_API_KEY:
        # Return mock agent for testing
        return {
            "agent_id": f"mock_agent_{voice_id}",
            "voice_id": voice_id,
            "language": language,
            "mock": True
        }
    
    url = f"{ELEVENLABS_API_BASE}/v1/convai/agents/create"
    
    # Create conversational config with voice settings
    conversation_config = {
        "agent": {
            "prompt": {
                "prompt": f"You are a helpful voice assistant conducting a survey titled '{form_title}'. "
                         f"Ask questions one at a time in a natural, conversational way. "
                         f"Be patient, empathetic, and encouraging. If users go off-topic, "
                         f"gently redirect them back to the survey. Always respond in {language if language != 'hi' else 'Hindi'}."
            },
            "first_message": f"Hello! I'd like to ask you a few questions for the {form_title}. Are you ready to begin?",
            "language": language
        },
        "tts": {
            "voice_id": voice_id,
            "model": "eleven_turbo_v2_5",  # Low latency model
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True
        },
        "stt": {
            "model": "nova-2",
            "language": language
        }
    }
    
    payload = {
        "conversation_config": conversation_config,
        "name": f"Form Agent - {form_title}",
        "tags": ["barmuda", "form_survey", f"lang_{language}"]
    }
    
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
        resp.raise_for_status()
        
        agent_data = resp.json()
        logging.info(f"Created ElevenLabs agent: {agent_data.get('agent_id')}")
        
        return {
            "agent_id": agent_data.get("agent_id"),
            "voice_id": voice_id,
            "language": language,
            "created": True
        }
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to create ElevenLabs agent: {str(e)}")
        
        # Return mock agent as fallback
        return {
            "agent_id": f"mock_agent_{voice_id}",
            "voice_id": voice_id,
            "language": language,
            "error": str(e),
            "mock": True
        }


def get_or_create_agent_for_voice(voice_id: str, language: str = "en", form_title: str = "Survey") -> str:
    """Get or create an agent ID for the given voice.
    
    For now, this uses a simple mapping approach. In production, you might want to:
    1. Create agents via ElevenLabs dashboard
    2. Store agent_id mappings in Firebase
    3. Use pre-created agent IDs
    
    Returns:
        agent_id string
    """
    # Try creating an agent first, fall back to voice_id if it fails
    agent_result = create_conversational_agent(voice_id, language, form_title)
    
    if agent_result.get("created") and not agent_result.get("mock"):
        return agent_result.get("agent_id")
    
    # If agent creation fails, use voice_id directly as agent_id
    # This might work if the voice_id is also a valid agent_id in your ElevenLabs account
    return voice_id


def create_ephemeral_token(voice_id: str, language: str = "en", form_title: str = "Survey") -> Dict:
    """Request a short-lived ElevenLabs token for WebRTC sessions.
    
    This function tries to get a token for a conversational agent.
    """
    if not ELEVENLABS_API_KEY:
        # Return mock token for testing when API key is missing
        return {
            "token": "mock_token_for_voice_testing", 
            "expires_in": 3600,
            "voice_id": voice_id,
            "agent_id": f"mock_agent_{voice_id}"
        }
    
    # Get or create agent ID
    agent_id = get_or_create_agent_for_voice(voice_id, language, form_title)
    
    # Try multiple token endpoints (the API might have changed)
    token_endpoints = [
        f"{ELEVENLABS_API_BASE}/v1/convai/conversation/token",
        f"{ELEVENLABS_API_BASE}/v1/convai/token"
    ]
    
    last_error = None
    
    for url in token_endpoints:
        try:
            # Try GET method first
            resp = requests.get(url, params={"agent_id": agent_id}, headers=_headers(), timeout=10)
            
            if resp.status_code == 200:
                token_data = resp.json()
                token_data.update({
                    "voice_id": voice_id,
                    "agent_id": agent_id,
                    "language": language
                })
                logging.info(f"Generated token for agent {agent_id} via {url}")
                return token_data
                
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            logging.warning(f"Token endpoint {url} failed: {str(e)}")
            continue
    
    # If all endpoints fail, check if voice_id itself is a working agent_id
    if voice_id != agent_id:
        try:
            url = f"{ELEVENLABS_API_BASE}/v1/convai/conversation/token"
            resp = requests.get(url, params={"agent_id": voice_id}, headers=_headers(), timeout=10)
            
            if resp.status_code == 200:
                token_data = resp.json()
                token_data.update({
                    "voice_id": voice_id,
                    "agent_id": voice_id,
                    "language": language
                })
                logging.info(f"Generated token using voice_id as agent_id: {voice_id}")
                return token_data
                
        except requests.exceptions.RequestException as e:
            last_error = str(e)
    
    # All methods failed, return mock token with error info
    logging.error(f"All token generation methods failed. Last error: {last_error}")
    
    return {
        "token": f"mock_token_all_failed_{agent_id}", 
        "expires_in": 3600,
        "voice_id": voice_id,
        "agent_id": agent_id,
        "error": last_error,
        "note": "Consider creating agents via ElevenLabs dashboard and using agent_id directly"
    }
