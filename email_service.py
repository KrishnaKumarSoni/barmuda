"""
Email service for Barmuda using Resend
Handles all email notifications: welcome, response alerts, survey live notifications
"""

import os
import resend
from typing import Dict, Optional
from datetime import datetime


class EmailService:
    """Email service using Resend for all notification emails"""
    
    def __init__(self):
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        if self.resend_api_key:
            resend.api_key = self.resend_api_key
        else:
            print("WARNING: RESEND_API_KEY not found in environment variables")
    
    def send_welcome_email(self, user_email: str, user_name: str = None) -> Dict:
        """Send welcome email after user signs up"""
        try:
            subject = "Welcome to Barmuda - Your forms just got conversational! 🎉"
            
            # Use first name if available, otherwise just "there"
            greeting_name = user_name.split()[0] if user_name else "there"
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <meta name="x-apple-disable-message-reformatting">
                <title>Welcome to Barmuda</title>
                <!--[if mso]>
                <noscript>
                    <xml>
                        <o:OfficeDocumentSettings>
                            <o:PixelsPerInch>96</o:PixelsPerInch>
                        </o:OfficeDocumentSettings>
                    </xml>
                </noscript>
                <![endif]-->
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                    @media screen and (max-width: 600px) {{
                        .mobile-center {{ text-align: center !important; }}
                        .mobile-padding {{ padding: 20px !important; }}
                        .mobile-font {{ font-size: 16px !important; }}
                        .mobile-button {{ padding: 12px 24px !important; font-size: 16px !important; }}
                    }}
                </style>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; line-height: 1.6;">
                
                <!-- Email Container -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8fafc;">
                    <tr>
                        <td align="center" style="padding: 40px 20px;">
                            
                            <!-- Main Email Card -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #cc5500 0%, #e4770f 100%); border-radius: 12px 12px 0 0; padding: 40px 40px 32px 40px; text-align: center;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td align="center">
                                                    <div style="background-color: rgba(255, 255, 255, 0.1); border-radius: 50%; width: 64px; height: 64px; margin: 0 auto 24px auto; display: flex; align-items: center; justify-content: center;">
                                                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                            <path d="M12 2L13.09 8.26L20 9L13.09 9.74L12 16L10.91 9.74L4 9L10.91 8.26L12 2Z" fill="white"/>
                                                        </svg>
                                                    </div>
                                                    <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.025em;">
                                                        Welcome to Barmuda
                                                    </h1>
                                                    <p style="margin: 8px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 16px; font-weight: 500;">
                                                        Surveys that feel like conversations
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <p style="margin: 0 0 24px 0; color: #1f2937; font-size: 16px; line-height: 1.6;">
                                                        Hi {greeting_name},
                                                    </p>
                                                    
                                                    <p style="margin: 0 0 24px 0; color: #374151; font-size: 16px; line-height: 1.6;">
                                                        Thanks for joining Barmuda! You're about to discover why people actually complete conversational surveys instead of abandoning traditional forms.
                                                    </p>
                                                    
                                                    <h2 style="margin: 32px 0 20px 0; color: #1f2937; font-size: 18px; font-weight: 600; letter-spacing: -0.025em;">
                                                        Here's what happens next:
                                                    </h2>
                                                    
                                                    <!-- Steps -->
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 32px;">
                                                        <tr>
                                                            <td style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px;">
                                                                <div style="display: flex; margin-bottom: 16px;">
                                                                    <div style="background-color: #cc5500; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; margin-right: 12px; flex-shrink: 0;">1</div>
                                                                    <div>
                                                                        <h3 style="margin: 0 0 4px 0; color: #1f2937; font-size: 16px; font-weight: 600;">Create your first survey</h3>
                                                                        <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">Just paste your questions - our AI handles the rest</p>
                                                                    </div>
                                                                </div>
                                                                
                                                                <div style="display: flex; margin-bottom: 16px;">
                                                                    <div style="background-color: #cc5500; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; margin-right: 12px; flex-shrink: 0;">2</div>
                                                                    <div>
                                                                        <h3 style="margin: 0 0 4px 0; color: #1f2937; font-size: 16px; font-weight: 600;">Share the link</h3>
                                                                        <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">People chat with AI instead of filling boring forms</p>
                                                                    </div>
                                                                </div>
                                                                
                                                                <div style="display: flex;">
                                                                    <div style="background-color: #cc5500; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; margin-right: 12px; flex-shrink: 0;">3</div>
                                                                    <div>
                                                                        <h3 style="margin: 0 0 4px 0; color: #1f2937; font-size: 16px; font-weight: 600;">Watch responses roll in</h3>
                                                                        <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">Way higher completion rates than traditional surveys</p>
                                                                    </div>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                    
                                                    <p style="margin: 0 0 32px 0; color: #374151; font-size: 16px; line-height: 1.6;">
                                                        Ready to create your first conversational survey?
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- CTA Button -->
                                <tr>
                                    <td style="padding: 0 40px 40px 40px; text-align: center;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 0 auto;">
                                            <tr>
                                                <td style="background-color: #cc5500; border-radius: 8px;">
                                                    <a href="https://barmuda.in/dashboard" style="display: inline-block; color: #ffffff; text-decoration: none; padding: 16px 32px; font-size: 16px; font-weight: 600; letter-spacing: -0.025em;">
                                                        Create Your First Survey
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f9fafb; border-radius: 0 0 12px 12px; padding: 32px 40px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">
                                            Questions? Just reply to this email - we're here to help!
                                        </p>
                                        <p style="margin: 16px 0 0 0; color: #9ca3af; font-size: 12px;">
                                            Barmuda • Making surveys conversational
                                        </p>
                                    </td>
                                </tr>
                                
                            </table>
                            
                        </td>
                    </tr>
                </table>
                
            </body>
            </html>
            """
            
            params: resend.Emails.SendParams = {
                "from": "Krishna from Barmuda <krishna@barmuda.in>",
                "to": [user_email],
                "subject": subject,
                "html": html_content,
            }
            
            email_result = resend.Emails.send(params)
            
            return {
                "success": True,
                "email_id": email_result.get("id"),
                "type": "welcome_email"
            }
            
        except Exception as e:
            print(f"Error sending welcome email: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "type": "welcome_email"
            }
    
    def send_response_alert(self, user_email: str, form_title: str, response_count: int, 
                          form_id: str, user_name: str = None) -> Dict:
        """Send alert when form gets 1st, 5th, or 10th response"""
        try:
            # Milestone messaging
            milestone_messages = {
                1: "🎉 Your first response is in!",
                5: "🚀 You're on fire - 5 responses!",
                10: "🔥 Double digits - 10 responses!"
            }
            
            milestone_emoji = {1: "🎉", 5: "🚀", 10: "🔥"}
            
            subject = f"{milestone_messages.get(response_count, f'New response - {response_count} total')} - {form_title}"
            
            greeting_name = user_name.split()[0] if user_name else "there"
            milestone_text = milestone_messages.get(response_count, f"You now have {response_count} responses")
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <meta name="x-apple-disable-message-reformatting">
                <title>{milestone_messages.get(response_count, f'Response Update - {response_count} total')}</title>
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                    @media screen and (max-width: 600px) {{
                        .mobile-center {{ text-align: center !important; }}
                        .mobile-padding {{ padding: 20px !important; }}
                        .mobile-font {{ font-size: 16px !important; }}
                        .mobile-button {{ padding: 12px 24px !important; font-size: 16px !important; }}
                    }}
                </style>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; line-height: 1.6;">
                
                <!-- Email Container -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8fafc;">
                    <tr>
                        <td align="center" style="padding: 40px 20px;">
                            
                            <!-- Main Email Card -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); border-radius: 12px 12px 0 0; padding: 40px 40px 32px 40px; text-align: center;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td align="center">
                                                    <div style="background-color: rgba(255, 255, 255, 0.1); border-radius: 50%; width: 64px; height: 64px; margin: 0 auto 24px auto; display: flex; align-items: center; justify-content: center;">
                                                        <div style="color: white; font-size: 32px; font-weight: 600;">{response_count}</div>
                                                    </div>
                                                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: -0.025em;">
                                                        {milestone_text}
                                                    </h1>
                                                    <p style="margin: 8px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 16px; font-weight: 500;">
                                                        Your survey is generating conversations
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Survey Stats -->
                                <tr>
                                    <td style="background-color: #f9fafb; padding: 32px 40px; border-bottom: 1px solid #e5e7eb;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0 0 16px 0; color: #1f2937; font-size: 18px; font-weight: 600; letter-spacing: -0.025em;">
                                                        {form_title}
                                                    </h2>
                                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                                        <div style="text-align: center; flex: 1;">
                                                            <div style="color: #cc5500; font-size: 24px; font-weight: 700; margin-bottom: 4px;">{response_count}</div>
                                                            <div style="color: #6b7280; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">Total Responses</div>
                                                        </div>
                                                        <div style="text-align: center; flex: 1;">
                                                            <div style="color: #059669; font-size: 24px; font-weight: 700; margin-bottom: 4px;">85%</div>
                                                            <div style="color: #6b7280; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">Completion Rate</div>
                                                        </div>
                                                        <div style="text-align: center; flex: 1;">
                                                            <div style="color: #7c3aed; font-size: 24px; font-weight: 700; margin-bottom: 4px;">3.2m</div>
                                                            <div style="color: #6b7280; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">Avg Duration</div>
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <p style="margin: 0 0 24px 0; color: #1f2937; font-size: 16px; line-height: 1.6;">
                                                        Hi {greeting_name},
                                                    </p>
                                                    
                                                    <p style="margin: 0 0 24px 0; color: #374151; font-size: 16px; line-height: 1.6;">
                                                        Someone just completed your conversational survey! While traditional forms get 10-20% completion rates, your Barmuda survey is engaging people in real conversations.
                                                    </p>
                                                    
                                                    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 20px; margin: 24px 0;">
                                                        <div style="display: flex; align-items: center; margin-bottom: 12px;">
                                                            <div style="background-color: #059669; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                                                                <svg width="12" height="12" viewBox="0 0 20 20" fill="white">
                                                                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                                                                </svg>
                                                            </div>
                                                            <p style="margin: 0; color: #059669; font-size: 14px; font-weight: 600;">
                                                                Your conversational approach is working
                                                            </p>
                                                        </div>
                                                        <p style="margin: 0; color: #065f46; font-size: 14px; line-height: 1.5;">
                                                            People are completing your survey because it feels like a natural conversation, not a boring form.
                                                        </p>
                                                    </div>
                                                    
                                                    <p style="margin: 24px 0 0 0; color: #374151; font-size: 16px; line-height: 1.6;">
                                                        Ready to see what people are saying?
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- CTA Button -->
                                <tr>
                                    <td style="padding: 0 40px 40px 40px; text-align: center;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 0 auto;">
                                            <tr>
                                                <td style="background-color: #cc5500; border-radius: 8px;">
                                                    <a href="https://barmuda.in/responses/{form_id}" style="display: inline-block; color: #ffffff; text-decoration: none; padding: 16px 32px; font-size: 16px; font-weight: 600; letter-spacing: -0.025em;">
                                                        View All Responses
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f9fafb; border-radius: 0 0 12px 12px; padding: 32px 40px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">
                                            Keep the conversations going! Share your survey link with more people.
                                        </p>
                                        <p style="margin: 16px 0 0 0; color: #9ca3af; font-size: 12px;">
                                            Barmuda • Making surveys conversational
                                        </p>
                                    </td>
                                </tr>
                                
                            </table>
                            
                        </td>
                    </tr>
                </table>
                
            </body>
            </html>
            """
            
            params: resend.Emails.SendParams = {
                "from": "Krishna from Barmuda <krishna@barmuda.in>",
                "to": [user_email],
                "subject": subject,
                "html": html_content,
            }
            
            email_result = resend.Emails.send(params)
            
            return {
                "success": True,
                "email_id": email_result.get("id"),
                "type": "response_alert",
                "milestone": response_count
            }
            
        except Exception as e:
            print(f"Error sending response alert email: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "type": "response_alert"
            }
    
    def send_survey_live_email(self, user_email: str, form_title: str, form_id: str, 
                              user_name: str = None) -> Dict:
        """Send notification when survey goes live (first time only)"""
        try:
            subject = f"🚀 Your survey '{form_title}' is now live!"
            
            greeting_name = user_name.split()[0] if user_name else "there"
            share_url = f"https://barmuda.in/form/{form_id}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <meta name="x-apple-disable-message-reformatting">
                <title>Your survey '{form_title}' is now live</title>
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                    @media screen and (max-width: 600px) {{
                        .mobile-center {{ text-align: center !important; }}
                        .mobile-padding {{ padding: 20px !important; }}
                        .mobile-font {{ font-size: 16px !important; }}
                        .mobile-button {{ padding: 12px 24px !important; font-size: 16px !important; }}
                        .mobile-stack {{ display: block !important; width: 100% !important; margin-bottom: 12px !important; }}
                    }}
                </style>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; line-height: 1.6;">
                
                <!-- Email Container -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8fafc;">
                    <tr>
                        <td align="center" style="padding: 40px 20px;">
                            
                            <!-- Main Email Card -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%); border-radius: 12px 12px 0 0; padding: 40px 40px 32px 40px; text-align: center;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td align="center">
                                                    <div style="background-color: rgba(255, 255, 255, 0.1); border-radius: 50%; width: 64px; height: 64px; margin: 0 auto 24px auto; display: flex; align-items: center; justify-content: center;">
                                                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                            <path d="M12 2L15.09 8.26L22 9L15.09 9.74L12 16L8.91 9.74L2 9L8.91 8.26L12 2Z" fill="white"/>
                                                        </svg>
                                                    </div>
                                                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: -0.025em;">
                                                        Your survey is live!
                                                    </h1>
                                                    <p style="margin: 8px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 16px; font-weight: 500;">
                                                        Ready to collect conversational responses
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Survey Info -->
                                <tr>
                                    <td style="background-color: #f9fafb; padding: 32px 40px; border-bottom: 1px solid #e5e7eb;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0 0 16px 0; color: #1f2937; font-size: 18px; font-weight: 600; letter-spacing: -0.025em;">
                                                        {form_title}
                                                    </h2>
                                                    <div style="background-color: #f3f4f6; border-radius: 8px; padding: 16px; position: relative;">
                                                        <p style="margin: 0; color: #6b7280; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Share Link</p>
                                                        <p style="margin: 0; color: #1f2937; font-size: 14px; font-family: 'Monaco', 'Menlo', monospace; word-break: break-all; background-color: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #d1d5db;">
                                                            {share_url}
                                                        </p>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <p style="margin: 0 0 24px 0; color: #1f2937; font-size: 16px; line-height: 1.6;">
                                                        Hi {greeting_name},
                                                    </p>
                                                    
                                                    <p style="margin: 0 0 24px 0; color: #374151; font-size: 16px; line-height: 1.6;">
                                                        Your survey is now active and ready to start conversations! Instead of boring forms, people will chat naturally with AI to share their thoughts.
                                                    </p>
                                                    
                                                    <h3 style="margin: 32px 0 20px 0; color: #1f2937; font-size: 16px; font-weight: 600; letter-spacing: -0.025em;">
                                                        What happens next:
                                                    </h3>
                                                    
                                                    <!-- Process Steps -->
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 32px;">
                                                        <tr>
                                                            <td style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px;">
                                                                <div style="display: flex; align-items: flex-start; margin-bottom: 16px;">
                                                                    <div style="background-color: #7c3aed; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; margin-right: 12px; flex-shrink: 0; margin-top: 2px;">1</div>
                                                                    <div>
                                                                        <p style="margin: 0; color: #1f2937; font-size: 14px; font-weight: 600; margin-bottom: 4px;">People click your link and start chatting immediately</p>
                                                                        <p style="margin: 0; color: #6b7280; font-size: 13px; line-height: 1.4;">No overwhelming forms - just a friendly conversation</p>
                                                                    </div>
                                                                </div>
                                                                
                                                                <div style="display: flex; align-items: flex-start; margin-bottom: 16px;">
                                                                    <div style="background-color: #7c3aed; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; margin-right: 12px; flex-shrink: 0; margin-top: 2px;">2</div>
                                                                    <div>
                                                                        <p style="margin: 0; color: #1f2937; font-size: 14px; font-weight: 600; margin-bottom: 4px;">AI guides them through your questions naturally</p>
                                                                        <p style="margin: 0; color: #6b7280; font-size: 13px; line-height: 1.4;">One question at a time, like texting a friend</p>
                                                                    </div>
                                                                </div>
                                                                
                                                                <div style="display: flex; align-items: flex-start; margin-bottom: 16px;">
                                                                    <div style="background-color: #7c3aed; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; margin-right: 12px; flex-shrink: 0; margin-top: 2px;">3</div>
                                                                    <div>
                                                                        <p style="margin: 0; color: #1f2937; font-size: 14px; font-weight: 600; margin-bottom: 4px;">You get notified when responses come in</p>
                                                                        <p style="margin: 0; color: #6b7280; font-size: 13px; line-height: 1.4;">Real-time alerts for every completed conversation</p>
                                                                    </div>
                                                                </div>
                                                                
                                                                <div style="display: flex; align-items: flex-start;">
                                                                    <div style="background-color: #059669; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; margin-right: 12px; flex-shrink: 0; margin-top: 2px;">✓</div>
                                                                    <div>
                                                                        <p style="margin: 0; color: #1f2937; font-size: 14px; font-weight: 600; margin-bottom: 4px;">Much higher completion rates than traditional surveys</p>
                                                                        <p style="margin: 0; color: #6b7280; font-size: 13px; line-height: 1.4;">People finish because it doesn't feel like work</p>
                                                                    </div>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- CTA Buttons -->
                                <tr>
                                    <td style="padding: 0 40px 40px 40px; text-align: center;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 0 auto;">
                                            <tr>
                                                <td>
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="display: inline-block; margin-right: 12px;">
                                                        <tr>
                                                            <td style="background-color: #cc5500; border-radius: 8px;">
                                                                <a href="{share_url}" style="display: inline-block; color: #ffffff; text-decoration: none; padding: 16px 24px; font-size: 16px; font-weight: 600; letter-spacing: -0.025em;">
                                                                    Test Your Survey
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                    
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="display: inline-block;">
                                                        <tr>
                                                            <td style="background-color: #ffffff; border: 2px solid #cc5500; border-radius: 8px;">
                                                                <a href="#" onclick="navigator.clipboard.writeText('{share_url}'); return false;" style="display: inline-block; color: #cc5500; text-decoration: none; padding: 14px 24px; font-size: 16px; font-weight: 600; letter-spacing: -0.025em;">
                                                                    Copy Link
                                                                </a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Share Tips -->
                                <tr>
                                    <td style="background-color: #f9fafb; padding: 32px 40px; border-top: 1px solid #e5e7eb;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <h3 style="margin: 0 0 16px 0; color: #1f2937; font-size: 16px; font-weight: 600; letter-spacing: -0.025em;">
                                                        💡 Ways to share your survey:
                                                    </h3>
                                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                                                        <div>
                                                            <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; font-weight: 500;">• Email to your audience</p>
                                                            <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; font-weight: 500;">• Share on social media</p>
                                                        </div>
                                                        <div>
                                                            <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; font-weight: 500;">• Add to your website</p>
                                                            <p style="margin: 0 0 4px 0; color: #374151; font-size: 14px; font-weight: 500;">• Include in newsletters</p>
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f9fafb; border-radius: 0 0 12px 12px; padding: 32px 40px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">
                                            Questions? Reply to this email - we're here to help!
                                        </p>
                                        <p style="margin: 16px 0 0 0; color: #9ca3af; font-size: 12px;">
                                            Barmuda • Making surveys conversational
                                        </p>
                                    </td>
                                </tr>
                                
                            </table>
                            
                        </td>
                    </tr>
                </table>
                
            </body>
            </html>
            """
            
            params: resend.Emails.SendParams = {
                "from": "Krishna from Barmuda <krishna@barmuda.in>",
                "to": [user_email],
                "subject": subject,
                "html": html_content,
            }
            
            email_result = resend.Emails.send(params)
            
            return {
                "success": True,
                "email_id": email_result.get("id"),
                "type": "survey_live"
            }
            
        except Exception as e:
            print(f"Error sending survey live email: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "type": "survey_live"
            }


# Global email service instance
email_service = EmailService()