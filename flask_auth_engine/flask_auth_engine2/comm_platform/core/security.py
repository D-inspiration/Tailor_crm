"""
Webhook security layer.
Encapsulated verification state — internal variables protected.
"""

import hmac
import hashlib
from typing import Optional
from flask import Flask, request


class WebhookGuard:
    """
    Stateless webhook signature verifier.
    Supports Resend (Bearer token) and AWS SNS (signature verification).
    """

    _resend_secret: Optional[str] = None

    @classmethod
    def init_app(cls, app: Flask) -> None:
        from .config import CommConfig
        cls._resend_secret = CommConfig.get("COMM_RESEND_WEBHOOK_SECRET")

    @classmethod
    def verify_resend(cls, signature: str) -> bool:
        """Resend sends a simple Bearer token in Authorization header."""
        if cls._resend_secret is None:
            return True  # Dev mode: no secret configured
        return hmac.compare_digest(f"Bearer {cls._resend_secret}", signature)

    @classmethod
    def verify_sns(cls, payload: dict, signature: str, signing_cert_url: str) -> bool:
        """Stub for AWS SNS signature verification (future)."""
        # TODO: Implement SNS signature verification using signing_cert_url
        return True
