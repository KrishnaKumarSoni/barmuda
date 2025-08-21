#!/usr/bin/env python3
"""
Debug email delivery issues and check Resend status
"""

import os
import resend
from dotenv import load_dotenv
import time

load_dotenv()

def check_email_delivery():
    """Check which emails are being delivered"""
    
    resend.api_key = os.getenv("RESEND_API_KEY")
    
    print("🔍 Debugging Email Delivery Issues")
    print("=" * 50)
    
    # The issue might be:
    # 1. Gmail treating multiple rapid emails as spam
    # 2. Domain verification issues with barmuda.in
    # 3. From address not verified in Resend
    
    test_email = "krishnakumarconnects@gmail.com"
    
    print("\n📧 Sending emails with delays to avoid spam filters...")
    
    emails_to_send = [
        {
            "name": "Welcome Email",
            "subject": "Welcome to Barmuda - Test " + str(int(time.time())),
            "html": "<h1>Welcome Email Test</h1><p>This is test email 1 of 5</p>"
        },
        {
            "name": "First Response",
            "subject": "Your first response! - Test " + str(int(time.time())),
            "html": "<h1>First Response Test</h1><p>This is test email 2 of 5</p>"
        },
        {
            "name": "Fifth Response",
            "subject": "5 responses received! - Test " + str(int(time.time())),
            "html": "<h1>Fifth Response Test</h1><p>This is test email 3 of 5</p>"
        },
        {
            "name": "Tenth Response", 
            "subject": "10 responses! - Test " + str(int(time.time())),
            "html": "<h1>Tenth Response Test</h1><p>This is test email 4 of 5</p>"
        },
        {
            "name": "Survey Live",
            "subject": "Your survey is live! - Test " + str(int(time.time())),
            "html": "<h1>Survey Live Test</h1><p>This is test email 5 of 5</p>"
        }
    ]
    
    sent_count = 0
    failed_count = 0
    
    for i, email_data in enumerate(emails_to_send, 1):
        print(f"\n{i}. Sending {email_data['name']}...")
        
        try:
            # Try with a simpler from address first
            params = {
                "from": "onboarding@resend.dev",  # Using Resend's test domain
                "to": [test_email],
                "subject": email_data["subject"],
                "html": email_data["html"]
            }
            
            result = resend.Emails.send(params)
            print(f"   ✅ Sent! ID: {result.get('id')}")
            sent_count += 1
            
            # Wait 2 seconds between emails to avoid rate limiting
            if i < len(emails_to_send):
                print("   ⏳ Waiting 2 seconds before next email...")
                time.sleep(2)
                
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            failed_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {sent_count} sent, {failed_count} failed")
    
    print("\n💡 TROUBLESHOOTING TIPS:")
    print("1. Check Gmail's Spam/Promotions/Updates folders")
    print("2. The 'from' domain might need verification in Resend")
    print("3. Add 'hello@barmuda.in' as verified sender in Resend dashboard")
    print("4. Check Resend dashboard for delivery status")
    print("\n🔗 Resend Dashboard: https://resend.com/emails")
    
    return sent_count, failed_count

if __name__ == "__main__":
    check_email_delivery()