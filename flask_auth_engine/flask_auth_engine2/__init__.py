"""
Communication Platform Core
============================
Self-contained module that layers on top of an existing Flask app.

Usage in your existing app.py (add ONE line):
    from comm_platform import init_comm_platform
    init_comm_platform(app)

No existing files are modified.
"""

from flask import Flask
from .core.config import CommConfig
from .core.security import WebhookGuard

# Blueprints
from .blueprints.mail import mail_bp
from .blueprints.webhooks import webhooks_bp
from .blueprints.subscribers import subscribers_bp
from .blueprints.dashboard import dashboard_bp

# Models registration hook (SQLAlchemy)
from .models import message, subscriber, webhook_log, attachment

__all__ = ["init_comm_platform"]


def init_comm_platform(app: Flask) -> None:
    """
    Register all communication platform blueprints and services
    onto an existing Flask application instance.
    """
    # Load config overlay (reads from app.config, no overwriting)
    CommConfig.load(app)

    # Register URL prefixes
    app.register_blueprint(webhooks_bp, url_prefix="/webhooks")
    app.register_blueprint(mail_bp, url_prefix="/mail")
    app.register_blueprint(subscribers_bp, url_prefix="/subscribers")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    # Initialize webhook guard with app secret
    WebhookGuard.init_app(app)
