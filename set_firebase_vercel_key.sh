#!/bin/bash

# Extract the private key from JSON file and set it in Vercel
PRIVATE_KEY=$(python3 -c "
import json
with open('barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json') as f:
    data = json.load(f)
    # Clean the key and ensure proper escaping for Vercel
    key = data['private_key'].strip()
    # Replace actual newlines with literal \n for Vercel
    print(key.replace('\n', '\\\\n'))
")

echo "Setting Firebase private key in Vercel..."
echo "$PRIVATE_KEY" | npx vercel env add FIREBASE_PRIVATE_KEY production --stdin