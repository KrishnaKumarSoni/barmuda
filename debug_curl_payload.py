#!/usr/bin/env python3
"""Debug what curl is actually sending"""

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/debug', methods=['POST'])
def debug_payload():
    """Log exactly what curl sends"""
    try:
        raw_data = request.get_data(as_text=True)
        json_data = request.get_json()
        
        print("="*50)
        print("🔍 CURL PAYLOAD DEBUG")
        print("="*50)
        print(f"Raw data: {repr(raw_data)}")
        print(f"JSON data: {json_data}")
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        
        if json_data and 'message' in json_data:
            message = json_data['message']
            print(f"Message: {repr(message)}")
            print(f"Message bytes: {message.encode('utf-8')}")
            print(f"Contains exclamation: {'!' in message}")
            print(f"Message length: {len(message)}")
            
        return jsonify({"received": raw_data, "parsed": json_data})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    print("🔍 Starting debug server on port 5001...")
    print("Test with: curl -X POST http://localhost:5001/debug -H 'Content-Type: application/json' -d '{\"message\": \"test!\"}'")
    app.run(port=5001, debug=True)