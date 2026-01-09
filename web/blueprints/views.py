import logging
import os
from flask import Blueprint, render_template, redirect, url_for, session, request, send_from_directory
from web.utils.auth import login_required
from web.extensions import db
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime

logger = logging.getLogger(__name__)

views_bp = Blueprint('views', __name__)

@views_bp.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(views_bp.root_path, "../../static/assets"),
        "favicon.ico",
        mimetype="image/x-icon",
    )

@views_bp.route("/robots.txt")
def robots_txt():
    return send_from_directory(os.path.join(views_bp.root_path, "../../static"), "robots.txt")

@views_bp.route("/sitemap.xml")
def sitemap_xml():
    return send_from_directory(os.path.join(views_bp.root_path, "../../static"), "sitemap.xml")

@views_bp.route("/llms.txt")
def llms_txt():
    return send_from_directory(os.path.join(views_bp.root_path, "../../static"), "llms.txt")

@views_bp.route("/sw.js")
def service_worker():
    response = send_from_directory(os.path.join(views_bp.root_path, "../../static"), "sw.js")
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    return response

@views_bp.route("/")
def home():
    """Home page - redirect authenticated users to create-form, show landing page for anonymous"""
    if session.get("authenticated") and session.get("user_id"):
        return redirect(url_for("views.create_form"))
    return render_template("index.html")

@views_bp.route("/dashboard")
@login_required
def dashboard():
    """Protected dashboard route"""
    try:
        user_id = request.user["uid"]
        try:
            # Get forms for the user
            forms_ref = (
                db.collection("forms")
                .where(filter=FieldFilter("creator_id", "==", user_id))
                .order_by("created_at", direction="DESCENDING")
            )
            forms = []
            for doc in forms_ref.stream():
                form_data = doc.to_dict()
                form_data["form_id"] = doc.id
                
                # Simple response count
                responses_ref = db.collection("responses").where(
                    filter=FieldFilter("form_id", "==", doc.id)
                )
                response_docs = responses_ref.limit(100).stream()
                response_count = sum(1 for _ in response_docs)
                if response_count == 100:
                    response_count = "100+"
                form_data["response_count"] = response_count
                forms.append(form_data)
        except Exception as e:
            logger.warning(f"Index not ready or error: {e}")
            # Fallback without ordering
            forms_ref = db.collection("forms").where(
                filter=FieldFilter("creator_id", "==", user_id)
            )
            forms = []
            for doc in forms_ref.stream():
                form_data = doc.to_dict()
                form_data["form_id"] = doc.id
                forms.append(form_data)
            forms.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return render_template("dashboard.html", forms=forms, user=request.user)
    except Exception as e:
        logger.error(f"Failed to load dashboard: {e}")
        return "Internal server error", 500

@views_bp.route("/billing")
@login_required
def billing():
    """Protected billing route"""
    return render_template("billing.html", user=request.user)

@views_bp.route("/create-form")
@login_required
def create_form():
    """Form creation page"""
    return render_template("create_form.html", user=request.user)

@views_bp.route("/edit-form")
@login_required
def edit_form():
    """Form editing page"""
    return render_template("edit_form.html", user=request.user)

@views_bp.route("/pricing")
def pricing():
    return render_template("pricing.html")

@views_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@views_bp.route("/terms")
def terms():
    return render_template("terms.html")

@views_bp.route("/why")
def why():
    return render_template("why.html")

@views_bp.route("/guides")
def guides():
    return render_template("guides.html")

@views_bp.route("/guides/ai-user-interviews")
def ai_user_interviews_guide():
    return render_template("guides/ai-user-interviews.html")

@views_bp.route("/guides/conversational-vs-traditional-surveys")
def conversational_vs_traditional():
    return render_template("guides/conversational-vs-traditional.html")

@views_bp.route("/financial-consultants")
def financial_consultants():
    return render_template("financial-consultants.html")

@views_bp.route("/therapists")
def therapists():
    return render_template("therapists.html")

@views_bp.route("/market-research")
def market_research():
    return render_template("market-research.html")

@views_bp.route("/vs-typeform")
def vs_typeform():
    return render_template("comparisons/vs-typeform.html")

@views_bp.route("/vs-google-forms")
def vs_google_forms():
    return render_template("comparisons/vs-google-forms.html")
