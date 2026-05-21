"""
Communication Platform Core
============================
Self-contained module that layers on top of an existing Flask app.

Usage in your existing app.py (add ONE line):
    from comm_platform import init_comm_platform
    init_comm_platform(app)
"""

from flask import Flask
from .core.config import CommConfig
from .core.security import WebhookGuard
from .core.auth import DashboardAuth

# Blueprints
from .blueprints.mail.routes import mail_bp
from .blueprints.webhooks.routes import webhooks_bp
from .blueprints.subscribers.routes import subscribers_bp
from .blueprints.dashboard.routes import dashboard_bp

from .models import message, subscriber, webhook_log, attachment, sent_message

__all__ = ["init_comm_platform"]


def init_comm_platform(app: Flask) -> None:
    CommConfig.load(app)
    DashboardAuth.init_app(app)
    WebhookGuard.init_app(app)

    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")
    app.register_blueprint(mail_bp, url_prefix="/mail")
    app.register_blueprint(subscribers_bp, url_prefix="/subscribers")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")


