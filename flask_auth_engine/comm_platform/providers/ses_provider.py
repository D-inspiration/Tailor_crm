"""
AWS SES provider stub.
Implements the same interface for future migration.
"""

from typing import Dict, Any
from .base import EmailProvider
from ..core.security import WebhookGuard


class SESProvider(EmailProvider):
    """
    AWS Simple Email Service provider.
    Currently a stub — implements interface for polymorphic swapping.
    """

    @property
    def name(self) -> str:
        return "ses"

    def verify(self, payload: Dict[str, Any], signature: str) -> bool:
        return WebhookGuard.verify_sns(payload, signature, payload.get("SigningCertURL", ""))

    def receive(self, payload: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """
        SES sends SNS notifications with nested Message field.
        """
        message = payload.get("Message", {})
        return {
            "sender": message.get("mail", {}).get("source", ""),
            "recipient": message.get("mail", {}).get("destination", [""])[0],
            "subject": message.get("mail", {}).get("commonHeaders", {}).get("subject", ""),
            "body": message.get("content", ""),
            "html": None,
            "provider": self.name,
            "attachments": [],  # SES requires S3 extraction
        }
