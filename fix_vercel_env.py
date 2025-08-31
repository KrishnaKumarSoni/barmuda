#!/usr/bin/env python3
"""Script to fix Vercel Firebase environment variables"""

import json
import subprocess
import sys

# Read the service account JSON
with open('barmuda-in-firebase-adminsdk-fbsvc-c7e33f8c4f.json', 'r') as f:
    service_account = json.load(f)

# Get the private key and properly escape it for Vercel
private_key = service_account['private_key'].strip()
escaped_key = private_key.replace('\n', '\\n')

print("Setting FIREBASE_PRIVATE_KEY in Vercel...")
print(f"Key length: {len(escaped_key)} characters")

# Use echo and pipe to avoid interactive prompt
try:
    result = subprocess.run([
        'bash', '-c', 
        f'echo "{escaped_key}" | npx vercel env add FIREBASE_PRIVATE_KEY production'
    ], capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0:
        print("✅ Successfully set FIREBASE_PRIVATE_KEY in Vercel")
        print(result.stdout)
    else:
        print("❌ Failed to set environment variable")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
except subprocess.TimeoutExpired:
    print("⏰ Command timed out - may need manual intervention")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nIf automated setting failed, manually run:")
print("npx vercel env add FIREBASE_PRIVATE_KEY production")
print("And paste this key:")
print(escaped_key)