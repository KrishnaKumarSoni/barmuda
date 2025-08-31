import json

import requests

# Test session resumption
device_id = "fallback-1754153221962-xp3zft72b"
form_id = "x4GZrJ1165MiMze4YC2Y"

data = {"form_id": form_id, "device_id": device_id, "location": {}}

response = requests.post("http://127.0.0.1:5000/api/chat/start", json=data)

print("Response status:", response.status_code)
print("Response data:", json.dumps(response.json(), indent=2))
