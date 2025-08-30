#!/usr/bin/env python3
"""Fix Firebase credentials for Vercel deployment"""

import os
import json
import subprocess

# Get the Firebase private key from .env
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('FIREBASE_PRIVATE_KEY='):
            # Extract the key value (remove quotes and FIREBASE_PRIVATE_KEY=)
            private_key = line.split('=', 1)[1].strip().strip('"')
            break

# Create a properly formatted key for Vercel (with literal \n)
vercel_key = private_key.replace('\n', '\\n')

print("Private key format for Vercel:")
print(vercel_key)
print("\nRun this command:")
print(f'npx vercel env add FIREBASE_PRIVATE_KEY production')
print("Then paste the key above when prompted")