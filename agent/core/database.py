import os
from google.cloud import firestore
from google.oauth2 import service_account
from datetime import datetime
from typing import Dict, Any, Literal, cast
from dotenv import load_dotenv

load_dotenv()

# --- Firestore Client Initialization ---
def get_db_client():
    """
    Returns an initialized Firestore AsyncClient using environment variables.
    """
    # Prefer the explicit path variable you use in .env
    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    
    # Fallback to standard Google var if set
    if not cred_path:
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if cred_path and os.path.exists(cred_path):
        # print(f"[DB] Initializing Firestore AsyncClient with {cred_path}")
        return firestore.AsyncClient.from_service_account_json(cred_path)
    else:
        # print("[DB] Initializing Firestore AsyncClient with default credentials")
        return firestore.AsyncClient()

# Removed global db instance to prevent event loop conflicts

def get_utc_now() -> str:
    """Returns the current UTC time in ISO 8601 format with 'Z'."""
    return datetime.utcnow().isoformat() + "Z"

async def init_session(session_id: str, form_id: str) -> Dict[str, Any]:
    """
    Creates a new session document in Firestore if it doesn't exist.
    Returns the full session data.
    """
    db = get_db_client()
    try:
        session_ref = db.collection('sessions').document(session_id)
        session_doc = await session_ref.get()

        if session_doc.exists:
            print(f"[DB] Session {session_id} found. Loading...")
            return cast(Dict[str, Any], session_doc.to_dict())
        
        print(f"[DB] Creating new session for {session_id}...")
        
        new_doc = {
            "session_id": session_id,
            "form_id": form_id,
            "session_state": "ONGOING",
            "created_at": get_utc_now(),
            "last_updated": get_utc_now(),
            # responses map is strictly Key -> {value, status, timestamp}
            "responses": {} 
        }
        
        await session_ref.set(new_doc)
        return new_doc
    finally:
        db.close()

async def get_session_data(session_id: str) -> Dict[str, Any] | None:
    """
    Retrieves the session data from Firestore.
    """
    db = get_db_client()
    try:
        doc = await db.collection('sessions').document(session_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    finally:
        db.close()

async def update_response_in_db(
    session_id: str, 
    question_key: str, 
    value: Any, 
    status: Literal["ANSWERED", "SKIPPED", "UNASKED"]
):
    """
    Updates a specific question's data in the 'responses' map in Firestore
    using dot notation for nested fields.
    """
    db = get_db_client()
    try:
        session_ref = db.collection('sessions').document(session_id)
        
        # Use dot notation to update a field within the 'responses' map
        response_field_path = f'responses.{question_key}'
        
        await session_ref.update({
            response_field_path: {
                "value": value,
                "status": status,
                "timestamp": get_utc_now()
            },
            "last_updated": get_utc_now()
        })
    finally:
        db.close()

async def update_session_lifecycle(session_id: str, new_state: Literal["ONGOING", "FINISHED", "TERMINATED"]):
    """Updates the high-level status of the session in Firestore."""
    db = get_db_client()
    try:
        session_ref = db.collection('sessions').document(session_id)
        await session_ref.update({
            "session_state": new_state,
            "last_updated": get_utc_now()
        })
    finally:
        db.close()

async def get_form_schema(form_id: str) -> Dict[str, Any] | None:
    """
    Retrieves the form schema from the 'form' collection in Firestore.
    """
    db = get_db_client()
    try:
        # print("--- [Database] Fetching form schema for form_id:", form_id)
        doc = await db.collection('forms').document(form_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    finally:
        db.close()