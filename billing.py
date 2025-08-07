"""
Dodo Payments Integration for Barmuda
Handles subscription management, usage tracking, and payment processing
"""

import os
import json
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any

import requests
from firebase_admin import firestore

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Firestore client (will be passed in)
db = None

def init_billing(firestore_client):
    """Initialize billing module with Firestore client"""
    global db
    db = firestore_client

class DodoClient:
    """Dodo Payments API client"""
    
    def __init__(self, api_key: str, test_mode: bool = True):
        self.api_key = api_key
        self.test_mode = test_mode
        # Use correct base URLs from official documentation
        self.base_url = "https://test.dodopayments.com" if test_mode else "https://live.dodopayments.com"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_subscription_link(self, plan: str, customer_email: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
        """Create a subscription with payment link using correct Dodo API format"""
        try:
            # Map internal plan names to Dodo product IDs
            plan_mapping = {
                "starter": "pdt_6ItgPfxb3pNXVi0t6wCGt",    # Barmuda Starter
                "pro": "pdt_KjvNtH91A9YySlSeurvT7",        # Barmuda Professional
                "business": "contact_sales"                 # Business plan handled via sales
            }
            
            if plan not in plan_mapping:
                raise ValueError(f"Invalid plan: {plan}")
            
            # Handle business plan differently (contact sales)
            if plan_mapping[plan] == "contact_sales":
                return {"success": False, "error": "Business plan requires sales contact"}
            
            # Create subscription payload according to official API documentation
            payload = {
                "customer": {
                    "email": customer_email
                },
                "product_id": plan_mapping[plan],
                "payment_link": True,  # Generate payment link
                "return_url": success_url,
                "quantity": 1,
                "metadata": {
                    "plan": plan,
                    "source": "barmuda",
                    "cancel_url": cancel_url
                }
            }
            
            # Use correct endpoint: POST /subscriptions (not /payment-links)
            response = requests.post(
                f"{self.base_url}/subscriptions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract payment link from response
                payment_link = data.get("payment_link")
                if payment_link:
                    return {
                        "success": True, 
                        "checkout_url": payment_link,
                        "subscription_id": data.get("subscription_id"),
                        "data": data
                    }
                else:
                    return {"success": False, "error": "No payment link returned"}
            else:
                logger.error(f"Dodo API error: {response.status_code} - {response.text}")
                return {"success": False, "error": f"API Error: {response.status_code} - {response.text}"}
                
        except Exception as e:
            logger.error(f"Error creating subscription link: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription using correct Dodo API format"""
        try:
            # Use correct endpoint format - PUT request to update subscription status
            response = requests.put(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers=self.headers,
                json={"status": "cancelled"},
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Dodo cancel error: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def verify_webhook(self, payload: str, signature: str, webhook_secret: str, timestamp: str = None, webhook_id: str = None) -> bool:
        """Verify webhook signature using Dodo's standard webhook format"""
        try:
            # Dodo uses standard webhook format: webhook-id + webhook-timestamp + payload
            if timestamp and webhook_id:
                # Standard webhooks format: concatenate with periods
                message_to_sign = f"{webhook_id}.{timestamp}.{payload}"
            else:
                # Fallback to just payload if headers not available
                message_to_sign = payload
            
            expected_signature = hmac.new(
                webhook_secret.encode(),
                message_to_sign.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Handle different signature formats
            if signature.startswith("sha256="):
                signature = signature[7:]
            elif signature.startswith("v1,"):
                # Standard webhooks format
                signature = signature[3:]
                
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook: {str(e)}")
            return False


class SubscriptionManager:
    """Handles subscription logic and database operations"""
    
    # Plan configuration
    PLAN_LIMITS = {
        'free': {
            'conversations_per_month': 100,
            'max_forms': 3,
            'remove_branding': False,
            'custom_widget_colors': False,
            'template_library': False,
            'word_cloud': False,
            'advanced_export': False,
            'priority_support': False,
            'team_members': False
        },
        'starter': {
            'conversations_per_month': 1000,
            'max_forms': -1,  # unlimited
            'remove_branding': True,
            'custom_widget_colors': True,
            'template_library': True,
            'word_cloud': False,
            'advanced_export': False,
            'priority_support': False,
            'team_members': False
        },
        'pro': {
            'conversations_per_month': 10000,
            'max_forms': -1,
            'remove_branding': True,
            'custom_widget_colors': True,
            'template_library': True,
            'word_cloud': True,
            'advanced_export': True,
            'priority_support': True,
            'team_members': False
        },
        'business': {
            'conversations_per_month': -1,  # unlimited
            'max_forms': -1,
            'remove_branding': True,
            'custom_widget_colors': True,
            'template_library': True,
            'word_cloud': True,
            'advanced_export': True,
            'priority_support': True,
            'team_members': True
        }
    }
    
    def __init__(self):
        if not db:
            raise ValueError("Billing module not initialized. Call init_billing() first.")
    
    def get_user_subscription(self, user_id: str) -> Dict[str, Any]:
        """Get user's current subscription details"""
        try:
            user_ref = db.collection("users").document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                # Create user with free plan
                self._create_default_subscription(user_id)
                return self._get_default_subscription()
            
            user_data = user_doc.to_dict()
            subscription = user_data.get("subscription", {})
            
            # Ensure subscription has all required fields
            if not subscription or "plan" not in subscription:
                self._create_default_subscription(user_id)
                return self._get_default_subscription()
            
            return subscription
            
        except Exception as e:
            logger.error(f"Error getting user subscription: {str(e)}")
            return self._get_default_subscription()
    
    def _get_default_subscription(self) -> Dict[str, Any]:
        """Get default free subscription"""
        return {
            "plan": "free",
            "status": "active",
            "dodo_subscription_id": None,
            "current_period_end": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    def _create_default_subscription(self, user_id: str):
        """Create default subscription for new user"""
        try:
            user_ref = db.collection("users").document(user_id)
            subscription_data = self._get_default_subscription()
            
            user_ref.update({
                "subscription": subscription_data
            })
            
            # Initialize usage tracking
            self._init_usage_tracking(user_id)
            
        except Exception as e:
            logger.error(f"Error creating default subscription: {str(e)}")
    
    def _init_usage_tracking(self, user_id: str):
        """Initialize usage tracking for user"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            usage_ref = db.collection("usage_tracking").document(user_id)
            
            usage_data = {
                "user_id": user_id,
                "current_month": current_month,
                "conversations_count": 0,
                "forms_count": 0,
                "last_reset": datetime.now(),
                "created_at": datetime.now()
            }
            
            usage_ref.set(usage_data)
            
        except Exception as e:
            logger.error(f"Error initializing usage tracking: {str(e)}")
    
    def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """Get current month usage for user"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            usage_ref = db.collection("usage_tracking").document(user_id)
            usage_doc = usage_ref.get()
            
            if not usage_doc.exists:
                self._init_usage_tracking(user_id)
                return {
                    "conversations_count": 0,
                    "forms_count": 0,
                    "current_month": current_month
                }
            
            usage_data = usage_doc.to_dict()
            
            # Reset if month changed
            if usage_data.get("current_month") != current_month:
                self._reset_monthly_usage(user_id, current_month)
                return {
                    "conversations_count": 0,
                    "forms_count": 0,
                    "current_month": current_month
                }
            
            return {
                "conversations_count": usage_data.get("conversations_count", 0),
                "forms_count": usage_data.get("forms_count", 0),
                "current_month": current_month
            }
            
        except Exception as e:
            logger.error(f"Error getting user usage: {str(e)}")
            return {"conversations_count": 0, "forms_count": 0, "current_month": datetime.now().strftime("%Y-%m")}
    
    def _reset_monthly_usage(self, user_id: str, new_month: str):
        """Reset usage counters for new month"""
        try:
            usage_ref = db.collection("usage_tracking").document(user_id)
            usage_ref.update({
                "current_month": new_month,
                "conversations_count": 0,
                "forms_count": 0,
                "last_reset": datetime.now()
            })
        except Exception as e:
            logger.error(f"Error resetting monthly usage: {str(e)}")
    
    def can_create_form(self, user_id: str) -> Tuple[bool, str]:
        """Check if user can create a new form"""
        try:
            # Check if in test mode - allow unlimited
            if is_test_mode():
                logger.info("Test mode enabled - allowing unlimited form creation")
                return True, ""
            
            subscription = self.get_user_subscription(user_id)
            plan = subscription.get("plan", "free")
            limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS["free"])
            
            max_forms = limits["max_forms"]
            
            # Unlimited forms
            if max_forms == -1:
                return True, ""
            
            # Count current forms
            forms_ref = db.collection("forms").where("creator_id", "==", user_id)
            current_forms = len(list(forms_ref.stream()))
            
            if current_forms >= max_forms:
                return False, f"You've reached the maximum of {max_forms} forms for the {plan} plan. Upgrade to create more forms."
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking form creation: {str(e)}")
            return True, ""  # Allow on error
    
    def can_start_conversation(self, user_id: str) -> Tuple[bool, str]:
        """Check if user can start a new conversation"""
        try:
            # Check if in test mode - allow unlimited
            if is_test_mode():
                logger.info("Test mode enabled - allowing unlimited conversations")
                return True, ""
                
            subscription = self.get_user_subscription(user_id)
            plan = subscription.get("plan", "free")
            limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS["free"])
            
            conversations_limit = limits["conversations_per_month"]
            
            # Unlimited conversations
            if conversations_limit == -1:
                return True, ""
            
            usage = self.get_user_usage(user_id)
            current_conversations = usage["conversations_count"]
            
            if current_conversations >= conversations_limit:
                return False, f"You've reached the monthly limit of {conversations_limit} conversations for the {plan} plan. Upgrade for more conversations."
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking conversation limit: {str(e)}")
            return True, ""  # Allow on error
    
    def increment_conversation_count(self, user_id: str):
        """Increment conversation counter for user"""
        try:
            usage_ref = db.collection("usage_tracking").document(user_id)
            
            # Use transaction to avoid race conditions
            @firestore.transactional
            def update_count(transaction):
                usage_doc = usage_ref.get(transaction=transaction)
                if usage_doc.exists:
                    current_count = usage_doc.get("conversations_count") or 0
                    transaction.update(usage_ref, {
                        "conversations_count": current_count + 1,
                        "updated_at": datetime.now()
                    })
                else:
                    # Initialize if doesn't exist
                    self._init_usage_tracking(user_id)
                    transaction.update(usage_ref, {
                        "conversations_count": 1,
                        "updated_at": datetime.now()
                    })
            
            transaction = db.transaction()
            update_count(transaction)
            
        except Exception as e:
            logger.error(f"Error incrementing conversation count: {str(e)}")
    
    def increment_form_count(self, user_id: str):
        """Increment form counter for user"""
        try:
            usage_ref = db.collection("usage_tracking").document(user_id)
            
            @firestore.transactional
            def update_count(transaction):
                usage_doc = usage_ref.get(transaction=transaction)
                if usage_doc.exists:
                    current_count = usage_doc.get("forms_count") or 0
                    transaction.update(usage_ref, {
                        "forms_count": current_count + 1,
                        "updated_at": datetime.now()
                    })
                else:
                    self._init_usage_tracking(user_id)
                    transaction.update(usage_ref, {
                        "forms_count": 1,
                        "updated_at": datetime.now()
                    })
            
            transaction = db.transaction()
            update_count(transaction)
            
        except Exception as e:
            logger.error(f"Error incrementing form count: {str(e)}")
    
    def has_feature(self, user_id: str, feature: str) -> bool:
        """Check if user has access to a specific feature"""
        try:
            subscription = self.get_user_subscription(user_id)
            plan = subscription.get("plan", "free")
            limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS["free"])
            
            return limits.get(feature, False)
            
        except Exception as e:
            logger.error(f"Error checking feature access: {str(e)}")
            return False
    
    def update_subscription(self, user_id: str, plan: str, dodo_subscription_id: str = None):
        """Update user's subscription plan"""
        try:
            user_ref = db.collection("users").document(user_id)
            
            update_data = {
                "subscription.plan": plan,
                "subscription.status": "active",
                "subscription.updated_at": datetime.now()
            }
            
            if dodo_subscription_id:
                update_data["subscription.dodo_subscription_id"] = dodo_subscription_id
            
            user_ref.update(update_data)
            
            # Log subscription change
            self._log_subscription_event(user_id, "subscription_updated", {
                "new_plan": plan,
                "dodo_subscription_id": dodo_subscription_id
            })
            
        except Exception as e:
            logger.error(f"Error updating subscription: {str(e)}")
    
    def cancel_subscription(self, user_id: str):
        """Cancel user's subscription (downgrade to free)"""
        try:
            user_ref = db.collection("users").document(user_id)
            
            user_ref.update({
                "subscription.plan": "free",
                "subscription.status": "cancelled",
                "subscription.dodo_subscription_id": None,
                "subscription.updated_at": datetime.now()
            })
            
            self._log_subscription_event(user_id, "subscription_cancelled", {})
            
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
    
    def _log_subscription_event(self, user_id: str, event_type: str, data: Dict[str, Any]):
        """Log subscription events for auditing"""
        try:
            events_ref = db.collection("subscription_events")
            
            event_data = {
                "user_id": user_id,
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now()
            }
            
            events_ref.add(event_data)
            
        except Exception as e:
            logger.error(f"Error logging subscription event: {str(e)}")
    
    def get_user_invoices(self, user_id: str) -> list:
        """Get user's billing history"""
        try:
            invoices_ref = db.collection("invoices").where("user_id", "==", user_id).order_by("created_at", direction=firestore.Query.DESCENDING)
            invoices = []
            
            for doc in invoices_ref.stream():
                invoice_data = doc.to_dict()
                invoice_data["id"] = doc.id
                invoices.append(invoice_data)
            
            return invoices
            
        except Exception as e:
            logger.error(f"Error getting user invoices: {str(e)}")
            return []
    
    def save_invoice(self, user_id: str, invoice_data: Dict[str, Any]):
        """Save invoice from Dodo webhook"""
        try:
            invoice_ref = db.collection("invoices").document()
            
            invoice_doc = {
                "user_id": user_id,
                "dodo_invoice_id": invoice_data.get("id"),
                "amount": invoice_data.get("amount", 0),
                "currency": invoice_data.get("currency", "INR"),
                "status": invoice_data.get("status", "pending"),
                "plan": invoice_data.get("metadata", {}).get("plan", "unknown"),
                "billing_period": {
                    "start": invoice_data.get("period_start"),
                    "end": invoice_data.get("period_end")
                },
                "created_at": datetime.now(),
                "paid_at": invoice_data.get("paid_at")
            }
            
            invoice_ref.set(invoice_doc)
            
        except Exception as e:
            logger.error(f"Error saving invoice: {str(e)}")


# Initialize Dodo client
def get_dodo_client() -> Optional[DodoClient]:
    """Get configured Dodo client"""
    api_key = os.environ.get("DODO_API_KEY")
    if not api_key:
        logger.warning("DODO_API_KEY not configured")
        return None
    
    # Use test mode unless explicitly set to live mode
    test_mode = os.environ.get("DODO_TEST_MODE", "true").lower() == "true"
    return DodoClient(api_key, test_mode=test_mode)


# Initialize subscription manager
def get_subscription_manager() -> SubscriptionManager:
    """Get subscription manager instance"""
    return SubscriptionManager()


def is_test_mode() -> bool:
    """Check if billing is in test mode (unlimited usage)"""
    import os
    return os.environ.get("BILLING_TEST_MODE", "false").lower() == "true"