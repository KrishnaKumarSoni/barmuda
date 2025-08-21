#!/usr/bin/env python3
"""
Test script for Barmuda email notifications
Tests welcome email, response alerts, and survey live notifications
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from email_service import email_service
    print("✅ Successfully imported email_service")
except ImportError as e:
    print(f"❌ Failed to import email_service: {e}")
    sys.exit(1)

def test_welcome_email():
    """Test welcome email sending"""
    print("\n🧪 Testing Welcome Email...")
    
    result = email_service.send_welcome_email(
        user_email="test@example.com",
        user_name="Test User"
    )
    
    if result.get("success"):
        print(f"✅ Welcome email test successful! Email ID: {result.get('email_id')}")
        return True
    else:
        print(f"❌ Welcome email test failed: {result.get('error')}")
        return False

def test_response_alert():
    """Test response alert email sending"""
    print("\n🧪 Testing Response Alert Email...")
    
    # Test first response
    result = email_service.send_response_alert(
        user_email="test@example.com",
        form_title="Test Customer Survey",
        response_count=1,
        form_id="test_form_123",
        user_name="Test User"
    )
    
    if result.get("success"):
        print(f"✅ Response alert email test successful! Email ID: {result.get('email_id')}")
        return True
    else:
        print(f"❌ Response alert email test failed: {result.get('error')}")
        return False

def test_survey_live():
    """Test survey live email sending"""
    print("\n🧪 Testing Survey Live Email...")
    
    result = email_service.send_survey_live_email(
        user_email="test@example.com",
        form_title="Test Customer Survey",
        form_id="test_form_123",
        user_name="Test User"
    )
    
    if result.get("success"):
        print(f"✅ Survey live email test successful! Email ID: {result.get('email_id')}")
        return True
    else:
        print(f"❌ Survey live email test failed: {result.get('error')}")
        return False

def main():
    """Run all email tests"""
    print("🚀 Starting Barmuda Email Notification Tests")
    print("=" * 50)
    
    # Check if Resend API key is configured
    if not os.getenv("RESEND_API_KEY"):
        print("⚠️  RESEND_API_KEY not found in environment variables")
        print("   This will test the email generation but not actually send emails")
        print("   To actually send test emails, add RESEND_API_KEY to your .env file")
        print()
    
    tests = [
        ("Welcome Email", test_welcome_email),
        ("Response Alert", test_response_alert),
        ("Survey Live", test_survey_live),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All email notification tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)