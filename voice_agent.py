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


def create_ephemeral_token(agent_id: str) -> Dict:
    """Request a short-lived ElevenLabs token for WebRTC sessions."""
    url = f"{ELEVENLABS_API_BASE}/v1/convai/token"
    payload = {"agent_id": agent_id}
    resp = requests.post(url, json=payload, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()
