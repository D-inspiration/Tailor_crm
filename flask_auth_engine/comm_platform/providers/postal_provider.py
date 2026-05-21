"""
Postal (open-source mail server) provider stub.
"""

from typing import Dict, Any
from .base import EmailProvider


class PostalProvider(EmailProvider):
    """Postal.app provider stub."""

    @property
    def name(self) -> str:
        return "postal"

    def verify(self, payload: Dict[str, Any], signature: str) -> bool:
        # TODO: Implement Postal X-Postal-Signature verification
        return True

    def receive(self, payload: Dict[str, Any], signature: str) -> Dict[str, Any]:
        return {
            "sender": payload.get("from", ""),
            "recipient": payload.get("to", ""),
            "subject": payload.get("subject", ""),
            "body": payload.get("plain_body", ""),
            "html": payload.get("html_body", ""),
            "provider": self.name,
            "attachments": payload.get("attachments", []),
        }
