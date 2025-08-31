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
