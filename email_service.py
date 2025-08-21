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
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: 'DM Sans', Arial, sans-serif; margin: 0; padding: 20px; background-color: #fff5e0;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 12px; padding: 32px; border: 1px solid #fbe7bd;">
                    
                    <!-- Header -->
                    <div style="text-align: center; margin-bottom: 32px;">
                        <h1 style="color: #cc5500; font-size: 28px; font-weight: bold; margin: 0;">Welcome to Barmuda!</h1>
                        <p style="color: #666; font-size: 18px; margin: 8px 0 0 0;">Surveys that feel like texting</p>
                    </div>
                    
                    <!-- Main Content -->
                    <div style="margin-bottom: 32px;">
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
                            Hey {greeting_name} 👋
                        </p>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
                            Thanks for joining Barmuda! You're about to discover why people actually <em>complete</em> conversational surveys instead of abandoning boring forms.
                        </p>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
                            <strong>Here's what happens next:</strong>
                        </p>
                        
                        <div style="background-color: #fff5e0; padding: 20px; border-radius: 8px; border-left: 4px solid #cc5500; margin-bottom: 24px;">
                            <ol style="color: #333; font-size: 16px; line-height: 1.6; margin: 0; padding-left: 20px;">
                                <li style="margin-bottom: 8px;"><strong>Create your first survey:</strong> Just paste your questions - our AI handles the rest</li>
                                <li style="margin-bottom: 8px;"><strong>Share the link:</strong> People chat with AI instead of filling boring forms</li>
                                <li style="margin-bottom: 8px;"><strong>Watch responses roll in:</strong> Way higher completion rates than traditional surveys</li>
                            </ol>
                        </div>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
                            Ready to create your first conversational survey?
                        </p>
                    </div>
                    
                    <!-- CTA Button -->
                    <div style="text-align: center; margin-bottom: 32px;">
                        <a href="https://barmuda.in/dashboard" 
                           style="display: inline-block; background: linear-gradient(135deg, #cc5500, #d12b2e); color: white; text-decoration: none; padding: 14px 32px; border-radius: 50px; font-weight: 600; font-size: 16px;">
                            Create Your First Survey
                        </a>
                    </div>
                    
                    <!-- Footer -->
                    <div style="text-align: center; padding-top: 24px; border-top: 1px solid #fbe7bd;">
                        <p style="color: #666; font-size: 14px; margin: 0;">
                            Questions? Just reply to this email - we're here to help! 🚀
                        </p>
                    </div>
                    
                </div>
            </body>
            </html>
            """
            
            params: resend.Emails.SendParams = {
                "from": "Barmuda <hello@barmuda.in>",
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
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: 'DM Sans', Arial, sans-serif; margin: 0; padding: 20px; background-color: #fff5e0;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 12px; padding: 32px; border: 1px solid #fbe7bd;">
                    
                    <!-- Header -->
                    <div style="text-align: center; margin-bottom: 32px;">
                        <div style="font-size: 48px; margin-bottom: 16px;">{milestone_emoji.get(response_count, "📊")}</div>
                        <h1 style="color: #cc5500; font-size: 24px; font-weight: bold; margin: 0 0 8px 0;">{milestone_text}</h1>
                        <p style="color: #666; font-size: 16px; margin: 0;">Your survey is working!</p>
                    </div>
                    
                    <!-- Survey Info -->
                    <div style="background-color: #fff5e0; padding: 20px; border-radius: 8px; margin-bottom: 24px;">
                        <h2 style="color: #cc5500; font-size: 18px; font-weight: 600; margin: 0 0 12px 0;">Survey: {form_title}</h2>
                        <div style="color: #333; font-size: 16px;">
                            <strong>Total responses:</strong> {response_count}
                        </div>
                    </div>
                    
                    <!-- Main Content -->
                    <div style="margin-bottom: 32px;">
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
                            Hey {greeting_name} 👋
                        </p>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
                            Someone just completed your conversational survey! While traditional forms get 10-20% completion rates, your Barmuda survey is actually engaging people in real conversations.
                        </p>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
                            Ready to see what people are saying?
                        </p>
                    </div>
                    
                    <!-- CTA Button -->
                    <div style="text-align: center; margin-bottom: 32px;">
                        <a href="https://barmuda.in/responses/{form_id}" 
                           style="display: inline-block; background: linear-gradient(135deg, #cc5500, #d12b2e); color: white; text-decoration: none; padding: 14px 32px; border-radius: 50px; font-weight: 600; font-size: 16px;">
                            View All Responses
                        </a>
                    </div>
                    
                    <!-- Footer -->
                    <div style="text-align: center; padding-top: 24px; border-top: 1px solid #fbe7bd;">
                        <p style="color: #666; font-size: 14px; margin: 0;">
                            Keep the conversations going! Share your survey link with more people.
                        </p>
                    </div>
                    
                </div>
            </body>
            </html>
            """
            
            params: resend.Emails.SendParams = {
                "from": "Barmuda <notifications@barmuda.in>",
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
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: 'DM Sans', Arial, sans-serif; margin: 0; padding: 20px; background-color: #fff5e0;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 12px; padding: 32px; border: 1px solid #fbe7bd;">
                    
                    <!-- Header -->
                    <div style="text-align: center; margin-bottom: 32px;">
                        <div style="font-size: 48px; margin-bottom: 16px;">🚀</div>
                        <h1 style="color: #cc5500; font-size: 24px; font-weight: bold; margin: 0 0 8px 0;">Your survey is live!</h1>
                        <p style="color: #666; font-size: 16px; margin: 0;">Ready to collect conversational responses</p>
                    </div>
                    
                    <!-- Survey Info -->
                    <div style="background-color: #fff5e0; padding: 20px; border-radius: 8px; margin-bottom: 24px;">
                        <h2 style="color: #cc5500; font-size: 18px; font-weight: 600; margin: 0 0 12px 0;">Survey: {form_title}</h2>
                        <p style="color: #333; font-size: 14px; margin: 0; word-break: break-all;">
                            <strong>Share link:</strong> {share_url}
                        </p>
                    </div>
                    
                    <!-- Main Content -->
                    <div style="margin-bottom: 32px;">
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
                            Hey {greeting_name} 👋
                        </p>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
                            Your survey is now active and ready to start conversations! Instead of boring forms, people will chat naturally with AI to share their thoughts.
                        </p>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
                            <strong>What happens next:</strong>
                        </p>
                        
                        <div style="background-color: #f8f9fa; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
                            <ul style="color: #333; font-size: 16px; line-height: 1.6; margin: 0; padding-left: 20px;">
                                <li style="margin-bottom: 8px;">People click your link and start chatting immediately</li>
                                <li style="margin-bottom: 8px;">AI guides them through your questions naturally</li>
                                <li style="margin-bottom: 8px;">You get notified when responses come in</li>
                                <li>Much higher completion rates than traditional surveys!</li>
                            </ul>
                        </div>
                    </div>
                    
                    <!-- CTA Buttons -->
                    <div style="text-align: center; margin-bottom: 32px;">
                        <a href="{share_url}" 
                           style="display: inline-block; background: linear-gradient(135deg, #cc5500, #d12b2e); color: white; text-decoration: none; padding: 14px 32px; border-radius: 50px; font-weight: 600; font-size: 16px; margin-right: 16px; margin-bottom: 12px;">
                            Test Your Survey
                        </a>
                        
                        <a href="javascript:navigator.clipboard.writeText('{share_url}');" 
                           style="display: inline-block; background: white; color: #cc5500; text-decoration: none; padding: 14px 32px; border-radius: 50px; font-weight: 600; font-size: 16px; border: 2px solid #cc5500; margin-bottom: 12px;">
                            Copy Link
                        </a>
                    </div>
                    
                    <!-- Share Ideas -->
                    <div style="background-color: #fff5e0; padding: 20px; border-radius: 8px; margin-bottom: 24px;">
                        <h3 style="color: #cc5500; font-size: 16px; font-weight: 600; margin: 0 0 12px 0;">💡 Ways to share:</h3>
                        <ul style="color: #333; font-size: 14px; line-height: 1.5; margin: 0; padding-left: 20px;">
                            <li>Email to your audience</li>
                            <li>Share on social media</li>
                            <li>Add to your website</li>
                            <li>Include in newsletters</li>
                        </ul>
                    </div>
                    
                    <!-- Footer -->
                    <div style="text-align: center; padding-top: 24px; border-top: 1px solid #fbe7bd;">
                        <p style="color: #666; font-size: 14px; margin: 0;">
                            Questions? Reply to this email - we're here to help! 🎯
                        </p>
                    </div>
                    
                </div>
            </body>
            </html>
            """
            
            params: resend.Emails.SendParams = {
                "from": "Barmuda <notifications@barmuda.in>",
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