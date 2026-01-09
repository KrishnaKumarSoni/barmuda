import logging
from flask import Blueprint, jsonify, request
from web.utils.auth import login_required
from billing import get_subscription_manager

logger = logging.getLogger(__name__)

billing_bp = Blueprint('billing', __name__)

@billing_bp.route("/api/billing/plans")
def get_pricing_plans():
    """Get available pricing plans"""
    try:
        subscription_manager = get_subscription_manager()
        return jsonify({
            "success": True,
            "plans": {
                "free": {
                    "name": "Free",
                    "price": 0,
                    "currency": "USD",
                    "features": subscription_manager.PLAN_LIMITS["free"],
                },
                "starter": {
                    "name": "Starter",
                    "price": 19,
                    "currency": "USD",
                    "features": subscription_manager.PLAN_LIMITS["starter"],
                },
                "pro": {
                    "name": "Pro",
                    "price": 49,
                    "currency": "USD",
                    "features": subscription_manager.PLAN_LIMITS["pro"],
                },
                "business": {
                    "name": "Business",
                    "price": "Custom",
                    "currency": "USD",
                    "features": subscription_manager.PLAN_LIMITS["business"],
                },
            },
        })
    except Exception as e:
        logger.error(f"Error getting pricing plans: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get pricing plans"}), 500

@billing_bp.route("/api/billing/subscription")
@login_required
def get_user_subscription():
    """Get current user's subscription details"""
    try:
        user_id = request.user["uid"]
        subscription_manager = get_subscription_manager()

        subscription = subscription_manager.get_user_subscription(user_id)
        usage = subscription_manager.get_user_usage(user_id)
        plan = subscription.get("plan", "free")
        limits = subscription_manager.PLAN_LIMITS.get(plan, subscription_manager.PLAN_LIMITS["free"])

        return jsonify({
            "success": True,
            "subscription": subscription,
            "usage": usage,
            "limits": limits,
            "plan_features": {
                "remove_branding": subscription_manager.has_feature(user_id, "remove_branding"),
                "custom_widget_colors": subscription_manager.has_feature(user_id, "custom_widget_colors"),
                "template_library": subscription_manager.has_feature(user_id, "template_library"),
                "word_cloud": subscription_manager.has_feature(user_id, "word_cloud"),
                "advanced_export": subscription_manager.has_feature(user_id, "advanced_export"),
                "priority_support": subscription_manager.has_feature(user_id, "priority_support"),
                "team_members": subscription_manager.has_feature(user_id, "team_members"),
            },
        })
    except Exception as e:
        logger.error(f"Error getting user subscription: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get subscription"}), 500
