import requests
import json

# Test off-topic "bananas" redirect
session_id = "session_20250802_222406_c9664884"

# Send an off-topic message
data = {
    "session_id": session_id,
    "message": "Tell me about the latest AI news"
}

response = requests.post(
    "http://127.0.0.1:5000/api/chat/message",
    json=data
)

print("Response status:", response.status_code)
print("Response data:", json.dumps(response.json(), indent=2))