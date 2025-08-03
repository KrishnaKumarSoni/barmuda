import requests
import json

# Create a new session
device_id = "test-device-ended-session"
form_id = "x4GZrJ1165MiMze4YC2Y"

# Start session
start_data = {"form_id": form_id, "device_id": device_id, "location": {}}

response = requests.post("http://127.0.0.1:5000/api/chat/start", json=start_data)

session_data = response.json()
session_id = session_data["session_id"]
print(f"Created session: {session_id}")

# Send message to end the session
end_data = {
    "session_id": session_id,
    "message": "I'm done with this form, please end it",
}

response = requests.post("http://127.0.0.1:5000/api/chat/message", json=end_data)

print("End response:", json.dumps(response.json(), indent=2))

# Now try to resume the ended session
print("\nTrying to resume ended session...")
response = requests.post("http://127.0.0.1:5000/api/chat/start", json=start_data)

print("Resume response:", json.dumps(response.json(), indent=2))
