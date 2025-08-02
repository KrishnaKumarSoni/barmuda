#!/usr/bin/env python3
"""
Minimal test to check basic Flask functionality on Vercel
"""
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def test():
    firebase_env = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    return f"""
    <h1>Bermuda Test</h1>
    <p>Basic Flask working: ✅</p>
    <p>Firebase env var present: {'✅' if firebase_env else '❌'}</p>
    <p>Firebase env var length: {len(firebase_env) if firebase_env else 0}</p>
    """

if __name__ == '__main__':
    app.run(debug=True)