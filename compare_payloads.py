#!/usr/bin/env python3
"""Compare payloads from curl vs Python requests"""

import requests
import json
import subprocess

def compare_exclamation_handling():
    """Compare how curl vs Python handles exclamation marks"""
    
    test_data = {"session_id": "test", "message": "done!"}
    
    print("🔍 PAYLOAD COMPARISON")
    print("="*50)
    
    # Python requests approach
    print("1️⃣ Python requests JSON:")
    python_json = json.dumps(test_data)
    print(f"   String: {repr(python_json)}")
    print(f"   Bytes: {python_json.encode('utf-8')}")
    print(f"   Length: {len(python_json)}")
    
    # What curl would send with single quotes
    curl_payload = '{"session_id": "test", "message": "done!"}'
    print("\n2️⃣ Curl payload (single quotes):")
    print(f"   String: {repr(curl_payload)}")
    print(f"   Bytes: {curl_payload.encode('utf-8')}")
    print(f"   Length: {len(curl_payload)}")
    
    # Check if they're identical
    print(f"\n3️⃣ Are they identical? {python_json == curl_payload}")
    
    # Character by character comparison
    if python_json != curl_payload:
        print("\n4️⃣ Character-by-character diff:")
        for i, (a, b) in enumerate(zip(python_json, curl_payload)):
            if a != b:
                print(f"   Position {i}: Python='{a}' ({ord(a)}), Curl='{b}' ({ord(b)})")

if __name__ == "__main__":
    compare_exclamation_handling()