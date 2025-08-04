#!/usr/bin/env python3
"""
Test script for Barmuda MVP Module 1: Infrastructure & Authentication
Tests all authentication endpoints and user flows.
"""

import json
import time
from datetime import datetime

import requests

BASE_URL = "http://localhost:5000"


def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "status" in data, "Health check should include status"
        assert data["status"] == "healthy", "Status should be healthy"
        assert "firebase" in data, "Health check should include Firebase status"
        assert data["firebase"] == True, "Firebase should be initialized"

        print("✅ Health check passed")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_protected_route_without_auth():
    """Test that protected routes return 401 without authentication"""
    print("🔍 Testing protected route without authentication...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard")
        # Should redirect or return error for unauthenticated access
        assert response.status_code in [
            401,
            403,
            302,
        ], f"Expected auth error, got {response.status_code}"
        print("✅ Protected route correctly requires authentication")
        return True
    except Exception as e:
        print(f"❌ Protected route test failed: {e}")
        return False


def test_api_endpoint_without_auth():
    """Test API endpoint without authentication header"""
    print("🔍 Testing API endpoint without authentication...")
    try:
        response = requests.get(f"{BASE_URL}/api/user/profile")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

        data = response.json()
        assert "error" in data, "Should return error message"

        print("✅ API endpoint correctly requires authentication")
        return True
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False


def test_api_endpoint_with_invalid_token():
    """Test API endpoint with invalid authentication token"""
    print("🔍 Testing API endpoint with invalid token...")
    try:
        headers = {"Authorization": "Bearer invalid-token"}
        response = requests.get(f"{BASE_URL}/api/user/profile", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

        data = response.json()
        assert "error" in data, "Should return error message"

        print("✅ API endpoint correctly rejects invalid tokens")
        return True
    except Exception as e:
        print(f"❌ Invalid token test failed: {e}")
        return False


def test_auth_verify_without_token():
    """Test auth verification without token"""
    print("🔍 Testing auth verification without token...")
    try:
        response = requests.post(f"{BASE_URL}/auth/verify", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

        data = response.json()
        assert "error" in data, "Should return error message"

        print("✅ Auth verification correctly requires token")
        return True
    except Exception as e:
        print(f"❌ Auth verification test failed: {e}")
        return False


def test_auth_verify_with_invalid_token():
    """Test auth verification with invalid token"""
    print("🔍 Testing auth verification with invalid token...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/verify", json={"idToken": "invalid-token"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

        data = response.json()
        assert "valid" in data, "Should return valid status"
        assert data["valid"] == False, "Should be marked as invalid"

        print("✅ Auth verification correctly rejects invalid tokens")
        return True
    except Exception as e:
        print(f"❌ Auth verification invalid token test failed: {e}")
        return False


def test_google_auth_without_token():
    """Test Google auth without ID token"""
    print("🔍 Testing Google auth without token...")
    try:
        response = requests.post(f"{BASE_URL}/auth/google", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

        data = response.json()
        assert "error" in data, "Should return error message"

        print("✅ Google auth correctly requires ID token")
        return True
    except Exception as e:
        print(f"❌ Google auth test failed: {e}")
        return False


def test_home_page():
    """Test that home page loads correctly"""
    print("🔍 Testing home page...")
    try:
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/html" in response.headers.get(
            "content-type", ""
        ), "Should return HTML"

        print("✅ Home page loads correctly")
        return True
    except Exception as e:
        print(f"❌ Home page test failed: {e}")
        return False


def run_all_tests():
    """Run all authentication tests"""
    print("🚀 Starting Barmuda MVP Module 1 Authentication Tests")
    print("=" * 60)

    tests = [
        test_health_check,
        test_home_page,
        test_protected_route_without_auth,
        test_api_endpoint_without_auth,
        test_api_endpoint_with_invalid_token,
        test_auth_verify_without_token,
        test_auth_verify_with_invalid_token,
        test_google_auth_without_token,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All authentication tests passed! Module 1 is ready.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

    return failed == 0


if __name__ == "__main__":
    import sys

    # Check if running in interactive mode
    if sys.stdin.isatty():
        print(
            "⚠️  Make sure to start the Flask app with 'python app.py' before running tests!"
        )
        print("Press Enter to continue or Ctrl+C to cancel...")
        input()
    else:
        print(
            "🤖 Running in automated mode - assuming Flask app is running on localhost:5000"
        )
        time.sleep(2)  # Give Flask app time to start

    success = run_all_tests()
    exit(0 if success else 1)
