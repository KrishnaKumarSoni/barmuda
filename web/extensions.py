import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI
from google import genai
from google.genai import types
from web.config import Config

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        if os.environ.get("VERCEL") or os.environ.get("FIREBASE_PRIVATE_KEY"):
            # Production environment
            private_key = os.environ.get("FIREBASE_PRIVATE_KEY", "")
            # Robustly handle newline characters for Vercel env vars
            if "\\n" in private_key:
                private_key = private_key.replace("\\n", "\n")
            
            firebase_config = {
                "type": "service_account",
                "project_id": os.environ.get("FIREBASE_PROJECT_ID", "barmuda-in"),
                "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": private_key,
                "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('FIREBASE_CLIENT_EMAIL', '').replace('@', '%40')}",
                "universe_domain": "googleapis.com",
            }
            cred = credentials.Certificate(firebase_config)
            logger.info("Firebase configured with Vercel/Production credentials")
        else:
            # Local development
            service_account_path = os.environ.get(
                "FIREBASE_SERVICE_ACCOUNT_PATH",
                "barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json",
            )
            
            # Robust path resolution
            resolved_path = service_account_path
            if not os.path.exists(resolved_path):
                # Try resolving relative to project root (one level up from web/)
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                candidate_path = os.path.join(base_dir, service_account_path)
                if os.path.exists(candidate_path):
                    resolved_path = candidate_path
                    logger.info(f"Resolved Firebase credentials at: {resolved_path}")
                else:
                    # Try just the filename in current dir as last resort
                    filename = os.path.basename(service_account_path)
                    if os.path.exists(filename):
                        resolved_path = filename

            if os.path.exists(resolved_path):
                cred = credentials.Certificate(resolved_path)
                logger.info(f"Firebase configured with local file: {resolved_path}")
            else:
                logger.warning(f"Firebase service account file not found at {service_account_path} or {resolved_path}")
                cred = None
        
        if cred:
            firebase_admin.initialize_app(cred)
            logger.info("Firebase App Initialized Successfully")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to initialize Firebase: {e}", exc_info=True)
        # Re-raise because the app likely cannot function without DB
        raise e

# Global Extensions
db = firestore.client() if firebase_admin._apps else None

# --- LLM Clients ---
openai_client = None
if Config.OPENAI_API_KEY:
    openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

gemini_client = None
if Config.GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)

# --- Unified LLM Wrapper ---
def generate_text(
    system_prompt: str, 
    user_prompt: str, 
    model: str = None, 
    temperature: float = 0.1,
    response_mime_type: str = None,
    response_schema = None
) -> str:
    """
    Generates text using the configured LLM provider (OpenAI or Gemini).
    Supports structured output via response_mime_type and response_schema (Gemini only currently).
    """
    provider = Config.LLM_PROVIDER
    
    if provider == 'gemini':
        try:
            if not gemini_client:
                raise ValueError("Gemini API Key not configured")

            # Use gemini-2.0-flash as default for new SDK
            gemini_model_name = model or "gemini-2.0-flash"
            
            config_args = {
                "system_instruction": system_prompt,
                "temperature": temperature
            }
            
            if response_mime_type:
                config_args["response_mime_type"] = response_mime_type
            if response_schema:
                config_args["response_schema"] = response_schema

            response = gemini_client.models.generate_content(
                model=gemini_model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(**config_args)
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            # Fallback to OpenAI if configured
            if openai_client:
                logger.info("Falling back to OpenAI")
                provider = 'openai'
            else:
                raise e

    if provider == 'openai':
        if not openai_client:
            raise ValueError("OpenAI API Key not configured")
            
        gpt_model = model or "gpt-4o-mini"
        
        # OpenAI basic structured output fallback (JSON mode)
        response_format = None
        if response_mime_type == "application/json":
            response_format = {"type": "json_object"}

        response = openai_client.chat.completions.create(
            model=gpt_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content

    raise ValueError(f"Unknown LLM Provider: {provider}")
