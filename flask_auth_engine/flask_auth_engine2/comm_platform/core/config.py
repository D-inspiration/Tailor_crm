"""
Configuration overlay.
Reads from the existing Flask app.config without writing into it.
All keys are namespaced with COMM_ prefix to avoid collision.
"""

import os
from typing import Optional
from flask import Flask


class CommConfig:
    """Namespace-isolated configuration reader."""

    _app: Optional[Flask] = None

    DEFAULTS = {
        "COMM_RESEND_WEBHOOK_SECRET": os.getenv("RESEND_WEBHOOK_SECRET"),
        "COMM_SES_TOPIC_ARN": None,
        "COMM_MAX_ATTACHMENT_SIZE": 25 * 1024 * 1024,
        "COMM_SPAM_THRESHOLD": 70,
        "COMM_PREVIEW_LENGTH": 100,
        "COMM_DEFAULT_PROVIDER": "resend",
        "COMM_ENABLE_AI_SUMMARY": False,
        "COMM_DASHBOARD_PASSWORD": os.getenv("COMM_DASHBOARD_PASSWORD", "change-me-in-production"),
        "COMM_DASHBOARD_API_KEY": os.getenv("COMM_DASHBOARD_API_KEY"),
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
    }

    @classmethod
    def load(cls, app: Flask) -> None:
        cls._app = app
        for key, value in cls.DEFAULTS.items():
            app.config.setdefault(key, value)

    @classmethod
    def get(cls, key: str):
        if cls._app is None:
            raise RuntimeError("CommConfig not loaded. Call init_comm_platform(app) first.")
        return cls._app.config.get(key, cls.DEFAULTS.get(key))



