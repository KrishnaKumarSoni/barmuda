#!/usr/bin/env python3
"""
Simple test server to chat with agent v3
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from chat_agent_v3 import get_chat_agent
import json

app = Flask(__name__)
CORS(app)

# Initialize agent
chat_agent = get_chat_agent()

# Store sessions
sessions = {}

@app.route('/api/chat/start', methods=['POST'])
def start_chat():
    data = request.get_json()
    form_id = data.get('form_id', 'VhmJufviBBiuT1xUjypY')
    device_id = data.get('device_id', 'test_device')
    
    # Create new session
    session_id = chat_agent.create_session(form_id, device_id)
    sessions[session_id] = {'form_id': form_id, 'device_id': device_id}
    
    # Get initial greeting
    result = chat_agent.process_message(session_id, "Hello, I'm ready to start!")
    
    return jsonify({
        'session_id': session_id,
        'greeting': result['response'],
        'success': True
    })

@app.route('/api/chat/message', methods=['POST'])
def chat_message():
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')
    
    if not session_id or not message:
        return jsonify({'error': 'Missing session_id or message'}), 400
    
    # Process message
    result = chat_agent.process_message(session_id, message)
    
    return jsonify({
        'response': result['response'],
        'success': result['success'],
        'ended': result.get('metadata', {}).get('ended', False)
    })

if __name__ == '__main__':
    print("Starting test server on http://localhost:5001")
    app.run(port=5001, debug=True)