#!/bin/bash
# Set Firebase service account as environment variable in Vercel

FIREBASE_JSON=$(cat bermuda-01-firebase-adminsdk-fbsvc-660474f630.json | tr -d '\n' | tr -d ' ')

echo "Setting FIREBASE_SERVICE_ACCOUNT in Vercel..."
echo "$FIREBASE_JSON" | npx vercel env add FIREBASE_SERVICE_ACCOUNT production