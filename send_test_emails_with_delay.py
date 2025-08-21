#!/usr/bin/env python3
"""
Send test emails with delays to avoid rate limits
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_service import email_service

def send_test_emails_with_delay():
    """Send all email types with delays between them"""
    
    test_email = "krishnakumarconnects@gmail.com"
    test_name = "Krishna Kumar"
    
    print("📧 Sending test emails to:", test_email)
    print("⏳ Adding 1 second delay between emails to avoid rate limits")
    print("=" * 50)
    
    emails = [
        ("Welcome Email", lambda: email_service.send_welcome_email(test_email, test_name)),
        ("First Response Alert", lambda: email_service.send_response_alert(test_email, "Customer Survey", 1, "test123", test_name)),
        ("Fifth Response Alert", lambda: email_service.send_response_alert(test_email, "Employee Survey", 5, "test456", test_name)),
        ("Tenth Response Alert", lambda: email_service.send_response_alert(test_email, "Market Research", 10, "test789", test_name)),
        ("Survey Live", lambda: email_service.send_survey_live_email(test_email, "Product Feedback", "test999", test_name))
    ]
    
    successful = 0
    
    for i, (name, send_func) in enumerate(emails, 1):
        print(f"\n{i}. Sending {name}...")
        
        try:
            result = send_func()
            if result.get("success"):
                print(f"   ✅ Sent! ID: {result.get('email_id')}")
                successful += 1
            else:
                print(f"   ❌ Failed: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
        
        # Wait 1 second between emails (Resend allows 2 per second)
        if i < len(emails):
            print("   ⏳ Waiting 1 second...")
            time.sleep(1)
    
    print("\n" + "=" * 50)
    print(f"✅ Successfully sent {successful}/5 emails")
    print("\n📬 Check your Gmail inbox (and spam/promotions folders)")
    print("📱 All emails are mobile-responsive with 600px max-width")

if __name__ == "__main__":
    send_test_emails_with_delay()