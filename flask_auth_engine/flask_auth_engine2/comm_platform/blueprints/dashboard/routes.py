"""
Dashboard metrics API + HTML UI — stats, activity feed, health.
Protected by simple auth (session, API key, or password).
Templates and static files are served from blueprint-local folders.
"""

import os
from flask import Blueprint, jsonify, render_template, request, session
from ...services.mail_service import MailService
from ...services.subscription_service import SubscriptionService
from ...core.auth import DashboardAuth

# Point template and static folders to blueprint-local directories
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

dashboard_bp = Blueprint(
    "comm_dashboard",
    __name__,
    template_folder=template_dir,
    static_folder=static_dir,
    static_url_path="/static",
)

# ------------------------------------------------------------------
# API Routes (JSON)
# ------------------------------------------------------------------

@dashboard_bp.route("/stats", methods=["GET"])
@DashboardAuth.require
def stats():
    """Aggregate platform statistics."""
    mail = MailService()
    subs = SubscriptionService()
    return jsonify({
        "messages": mail.stats(),
        "subscribers": subs.stats(),
    })


@dashboard_bp.route("/health", methods=["GET"])
def health():
    """Service health check."""
    return jsonify({"status": "ok", "service": "comm_platform"})


# ------------------------------------------------------------------
# HTML Dashboard UI
# ------------------------------------------------------------------

@dashboard_bp.route("/ui", methods=["GET"])
@DashboardAuth.require
def dashboard_ui():
    """Serve the HTML dashboard UI."""
    return render_template("dashboard.html")


@dashboard_bp.route("/ui/login", methods=["GET", "POST"])
def dashboard_login():
    """
    Simple login page for dashboard access.
    If user already has session auth from main app, redirect to UI.
    """
    if DashboardAuth.check():
        return """<<script>window.location.href='/dashboard/ui'</script>"""

    if request.method == "POST":
        password = request.form.get("password", "")
        api_key = request.form.get("api_key", "")
        if DashboardAuth._password and password == DashboardAuth._password:
            session["comm_dashboard_auth"] = True
            return """<<script>window.location.href='/dashboard/ui'</script>"""
        if DashboardAuth._api_key and api_key == DashboardAuth._api_key:
            session["comm_dashboard_auth"] = True
            return """<<script>window.location.href='/dashboard/ui'</script>"""
        return render_template("login.html", error="Invalid credentials"), 401

    return render_template("login.html", error=None)
