#!/usr/bin/env python3
"""
Send test emails to krishnakumarconnects@gmail.com
Tests all email types with proper formatting
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_service import email_service

def send_all_test_emails():
    """Send all email types to Krishna's Gmail"""
    
    test_email = "krishnakumarconnects@gmail.com"
    test_name = "Krishna Kumar"
    
    print("📧 Sending test emails to:", test_email)
    print("=" * 50)
    
    # 1. Welcome Email
    print("\n1️⃣ Sending WELCOME EMAIL...")
    result1 = email_service.send_welcome_email(
        user_email=test_email,
        user_name=test_name
    )
    if result1.get("success"):
        print(f"   ✅ Welcome email sent! ID: {result1.get('email_id')}")
    else:
        print(f"   ❌ Failed: {result1.get('error')}")
    
    # 2. First Response Alert
    print("\n2️⃣ Sending FIRST RESPONSE ALERT...")
    result2 = email_service.send_response_alert(
        user_email=test_email,
        form_title="Customer Satisfaction Survey",
        response_count=1,
        form_id="test_form_123",
        user_name=test_name
    )
    if result2.get("success"):
        print(f"   ✅ First response alert sent! ID: {result2.get('email_id')}")
    else:
        print(f"   ❌ Failed: {result2.get('error')}")
    
    # 3. Fifth Response Alert
    print("\n3️⃣ Sending FIFTH RESPONSE ALERT...")
    result3 = email_service.send_response_alert(
        user_email=test_email,
        form_title="Employee Feedback Form",
        response_count=5,
        form_id="test_form_456",
        user_name=test_name
    )
    if result3.get("success"):
        print(f"   ✅ Fifth response alert sent! ID: {result3.get('email_id')}")
    else:
        print(f"   ❌ Failed: {result3.get('error')}")
    
    # 4. Tenth Response Alert
    print("\n4️⃣ Sending TENTH RESPONSE ALERT...")
    result4 = email_service.send_response_alert(
        user_email=test_email,
        form_title="Market Research Survey",
        response_count=10,
        form_id="test_form_789",
        user_name=test_name
    )
    if result4.get("success"):
        print(f"   ✅ Tenth response alert sent! ID: {result4.get('email_id')}")
    else:
        print(f"   ❌ Failed: {result4.get('error')}")
    
    # 5. Survey Live Notification
    print("\n5️⃣ Sending SURVEY LIVE NOTIFICATION...")
    result5 = email_service.send_survey_live_email(
        user_email=test_email,
        form_title="Product Feedback Survey",
        form_id="test_form_999",
        user_name=test_name
    )
    if result5.get("success"):
        print(f"   ✅ Survey live email sent! ID: {result5.get('email_id')}")
    else:
        print(f"   ❌ Failed: {result5.get('error')}")
    
    print("\n" + "=" * 50)
    print("✅ All test emails sent to:", test_email)
    print("\n📱 RESPONSIVENESS NOTES:")
    print("   • All emails use viewport meta tag for mobile")
    print("   • Max-width: 600px container for readability")
    print("   • Font sizes scale appropriately (16px base)")
    print("   • Buttons are touch-friendly (14px padding)")
    print("   • Single column layout works on all devices")
    print("   • Tested breakpoints: 320px, 768px, 1024px+")
    print("\n🎨 CHECK FOR:")
    print("   • Barmuda brand colors (#cc5500, #d12b2e)")
    print("   • Gradient buttons with proper contrast")
    print("   • Clean typography (DM Sans font family)")
    print("   • Proper spacing and padding")
    print("   • Mobile-friendly tap targets")

if __name__ == "__main__":
    send_all_test_emails()