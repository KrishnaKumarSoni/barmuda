#!/usr/bin/env python3
"""
Debug script to add to production to understand chat behavior
"""

# Add this debug code to app.py temporarily to understand what's happening

DEBUG_CODE = """
# Add to app.py after line 2143 (before agent = get_chat_agent())

        # DEBUG: Production chat investigation
        import sys
        print(f"DEBUG: Python version: {sys.version}", file=sys.stderr)
        print(f"DEBUG: Session ID: {session_id}", file=sys.stderr)
        print(f"DEBUG: User message: {message}", file=sys.stderr)
        
        try:
            print("DEBUG: Attempting to import chat_engine...", file=sys.stderr)
            from chat_engine import get_chat_agent
            print("DEBUG: Import successful", file=sys.stderr)
        except ImportError as e:
            print(f"DEBUG: Import failed: {e}", file=sys.stderr)
            # FALLBACK BEHAVIOR - This might be what's happening
            return jsonify({
                "response": "Interesting! " + message[:20] + "...",  # Generic response
                "success": True,
                "error": "chat_engine_import_failed"
            }), 200
        except Exception as e:
            print(f"DEBUG: Unexpected error: {e}", file=sys.stderr)
            
        try:
            print("DEBUG: Creating chat agent...", file=sys.stderr)
            agent = get_chat_agent()
            print("DEBUG: Agent created successfully", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: Agent creation failed: {e}", file=sys.stderr)
            # Another fallback
            return jsonify({
                "response": "Thanks for sharing that. " + message[:20] + "...",
                "success": True,
                "error": "agent_creation_failed"
            }), 200
"""

print(DEBUG_CODE)