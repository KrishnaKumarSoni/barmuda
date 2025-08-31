import logging
import os
from typing import Dict

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


def create_ephemeral_token(voice_id: str, form_data: Dict = None) -> Dict:
    """Request a short-lived ElevenLabs token for WebRTC voice sessions."""
    # For MVP, return a mock token structure for testing
    # In production, this would integrate with ElevenLabs Conversational AI
    return {
        "token": "mock_token_for_voice_testing",
        "expires_in": 3600,
        "voice_id": voice_id
    }


def generate_speech(text: str, voice_id: str) -> bytes:
    """Generate speech using ElevenLabs TTS API"""
    if not ELEVENLABS_API_KEY:
        raise ValueError("ElevenLabs API key not configured")
    
    url = f"{ELEVENLABS_API_BASE}/v1/text-to-speech/{voice_id}"
    
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True
        }
    }
    
    response = requests.post(url, json=payload, headers=_headers())
    response.raise_for_status()
    
    return response.content


def get_available_voices() -> Dict:
    """Get list of available ElevenLabs voices"""
    if not ELEVENLABS_API_KEY:
        return {"voices": []}
    
    url = f"{ELEVENLABS_API_BASE}/v1/voices"
    
    try:
        response = requests.get(url, headers=_headers())
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Failed to get voices: {e}")
        return {"voices": []}
