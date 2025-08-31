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


def create_ephemeral_token(voice_id: str, metadata: Optional[Dict] = None) -> Dict:
    """Request a short-lived ElevenLabs token for WebRTC voice sessions.

    ElevenLabs provides an endpoint for creating ephemeral conversation tokens
    which are required when establishing a WebRTC session with their
    Conversational AI SDK. This replaces the previous mocked token generation
    used during early development.
    """

    url = f"{ELEVENLABS_API_BASE}/v1/convai/tokens"

    payload: Dict[str, Dict] = {"voice_id": voice_id}
    if metadata:
        # Forward any metadata such as agent identifiers so it can be used by
        # ElevenLabs when creating the token.
        payload["metadata"] = metadata

    response = requests.post(url, json=payload, headers=_headers())
    response.raise_for_status()

    data = response.json()
    # Ensure voice_id is included so downstream callers have it available
    data.setdefault("voice_id", voice_id)
    return data


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
            "use_speaker_boost": True,
        },
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
