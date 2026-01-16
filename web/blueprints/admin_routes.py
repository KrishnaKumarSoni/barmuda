from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from admin import (
    admin_required, 
    verify_admin_password, 
    AdminMetrics, 
    log_admin_login,
    ADMIN_SESSION_KEY
)
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin_dashboard.html')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Support both form data and JSON
        if request.is_json:
            data = request.get_json()
            password = data.get('password')
        else:
            password = request.form.get('password')
            
        if verify_admin_password(password):
            session[ADMIN_SESSION_KEY] = True
            log_admin_login(True, request.remote_addr)
            if request.is_json:
                return jsonify({"success": True, "redirect": url_for('admin.dashboard')})
            return redirect(url_for('admin.dashboard'))
        else:
            log_admin_login(False, request.remote_addr)
            if request.is_json:
                return jsonify({"success": False, "error": "Invalid password"}), 401
            return render_template('admin_login.html', error="Invalid password")
    
    if session.get(ADMIN_SESSION_KEY):
        return redirect(url_for('admin.dashboard'))
        
    return render_template('admin_login.html')

@admin_bp.route('/logout', methods=['POST'])
def logout():
    session.pop(ADMIN_SESSION_KEY, None)
    return jsonify({"success": True})

# --- API Routes ---

@admin_bp.route('/api/dashboard')
@admin_required
def api_dashboard():
    try:
        metrics = AdminMetrics()
        return jsonify(metrics.get_dashboard_summary())
    except Exception as e:
        logger.error(f"Dashboard API error: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/trends')
@admin_required
def api_trends():
    period = request.args.get('period', 'L30D')
    try:
        metrics = AdminMetrics()
        return jsonify(metrics.get_trends_data(period))
    except Exception as e:
        logger.error(f"Trends API error: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/users/search')
@admin_required
def api_search_users():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    try:
        metrics = AdminMetrics()
        return jsonify(metrics.search_users(query))
    except Exception as e:
        logger.error(f"Search API error: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/users/recent')
@admin_required
def api_recent_users():
    try:
        metrics = AdminMetrics()
        return jsonify(metrics.get_recent_users())
    except Exception as e:
        logger.error(f"Recent users API error: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/users/<user_id>')
@admin_required
def api_user_details(user_id):
    try:
        metrics = AdminMetrics()
        details = metrics.get_user_details(user_id)
        if details:
            return jsonify(details)
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        logger.error(f"User details API error: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/users/<user_id>/grandfather', methods=['POST'])
@admin_required
def api_grandfather_user(user_id):
    try:
        metrics = AdminMetrics()
        success = metrics.grant_grandfather_status(user_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Grandfather API error: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/users/<user_id>/reset-usage', methods=['POST'])
@admin_required
def api_reset_usage(user_id):
    try:
        metrics = AdminMetrics()
        success = metrics.reset_user_usage(user_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Reset usage API error: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/users/<user_id>/forms')
@admin_required
def api_user_forms(user_id):
    try:
        metrics = AdminMetrics()
        return jsonify(metrics.get_user_forms(user_id))
    except Exception as e:
        logger.error(f"User forms API error: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/debug/counts')
@admin_required
def api_debug_counts():
    try:
        # Simple debug endpoint to check collection sizes directly
        from web.extensions import db
        users_count = len(list(db.collection("users").limit(100).stream()))
        forms_count = len(list(db.collection("forms_v2").limit(100).stream()))
        return jsonify({
            "users_sample": users_count,
            "forms_sample": forms_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
