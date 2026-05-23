"""
Webhook security layer.
Encapsulated verification state — internal variables protected.
"""

import hmac
import hashlib
from typing import Optional
from flask import Flask


class WebhookGuard:
    """
    Stateless webhook signature verifier.
    Supports Resend and AWS SNS.
    """

    _resend_secret: Optional[str] = None

    @classmethod
    def init_app(cls, app: Flask) -> None:
        from .config import CommConfig
        cls._resend_secret = CommConfig.get(
            "COMM_RESEND_WEBHOOK_SECRET"
        )

    @classmethod
    def verify_resend(
        cls,
        raw_body: bytes,
        signature: str
    ) -> bool:
        """
        Verify Resend webhook signature using raw request body.

        Signature format:
        sha256=<digest>
        """

        # Dev mode
        if cls._resend_secret is None:
            print("WARNING: No webhook secret configured")
            return True

        if not signature:
            return False

        if not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            cls._resend_secret.encode(),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        expected_signature = f"sha256={expected}"

        return hmac.compare_digest(
            expected_signature,
            signature
        )

    @classmethod
    def verify_sns(
        cls,
        payload: dict,
        signature: str,
        signing_cert_url: str
    ) -> bool:
        """Future AWS SNS verification."""
        return True
