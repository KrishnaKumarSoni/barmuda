import os
import sys
from flask import Flask

# Mock environment
os.environ['FLASK_ENV'] = 'development'

try:
    from web.extensions import db
    from google.cloud.firestore_v1.base_query import FieldFilter
    
    print(f"DB Object: {db}")
    
    if not db:
        print("CRITICAL: DB is None")
        sys.exit(1)
        
    print("Attempting query...")
    # Mock user_id (replace with a real one if known, or random string)
    user_id = "test_user_id"
    
    try:
        print("--- Testing Primary Query (Index Required) ---")
        forms_ref = (
            db.collection("forms_v2")
            .where(filter=FieldFilter("creator_id", "==", user_id))
            .order_by("created_at", direction="DESCENDING")
        )
        docs = list(forms_ref.stream())
        print(f"Primary Query Success. Found {len(docs)} docs.")
    except Exception as e:
        print(f"Primary Query Failed (Expected if no index): {e}")
        
        print("\n--- Testing Fallback Query (No Sort) ---")
        try:
            # Fallback: Client-side filtering/sorting
            forms_ref = db.collection("forms_v2").where(
                filter=FieldFilter("creator_id", "==", user_id)
            )
            docs = list(forms_ref.stream())
            print(f"Fallback Query Success. Found {len(docs)} docs.")
            
            # Simulate manual sort
            print("Simulating manual sort...")
            # Note: In real app, we access doc.to_dict() safely
            data = [d.to_dict() for d in docs]
            print(f"Loaded {len(data)} documents.")
            
        except Exception as fallback_e:
            print(f"Fallback Query CRITICAL FAILURE: {fallback_e}")
            import traceback
            traceback.print_exc()

except Exception as e:
    print(f"Setup Failed: {e}")
    import traceback
    traceback.print_exc()