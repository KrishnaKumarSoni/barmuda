import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get(
        "FLASK_SECRET_KEY",
        "dev-secret-key-for-local-testing-very-long-and-secure-123456789",
    )
    
    # Session configuration
    is_production = os.environ.get("VERCEL") or os.environ.get("PRODUCTION")
    SESSION_COOKIE_SECURE = bool(is_production)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "None" if is_production else "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_PERMANENT = True
    
    # LLM Configuration
    # Options: 'openai', 'gemini'
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'openai').lower()
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Other configs
    USE_GROQ = os.environ.get('USE_GROQ', 'false').lower() == 'true'
