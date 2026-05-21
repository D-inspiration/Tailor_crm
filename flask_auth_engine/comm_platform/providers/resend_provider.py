"""
Resend inbound email webhook provider.
"""

from typing import Dict, Any
from .base import EmailProvider
from ..core.security import WebhookGuard


class ResendProvider(EmailProvider):
    """
    Resend implementation of EmailProvider.
    Handles Resend-specific payload structure and signature verification.
    """

    @property
    def name(self) -> str:
        return "resend"

    def verify(self, payload: Dict[str, Any], signature: str) -> bool:
        return WebhookGuard.verify_resend(signature)

    def receive(self, payload: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """
        Transform Resend inbound payload to normalized message dict.
        Resend inbound payload structure:
        {
          "from": "sender@example.com",
          "to": ["recipient@example.com"],
          "subject": "...",
          "text": "...",
          "html": "...",
          "attachments": [{"filename": "...", "content": "base64...", "type": "..."}]
        }
        """
        return {
            "sender": payload.get("from", ""),
            "recipient": payload.get("to", [""])[0] if isinstance(payload.get("to"), list) else payload.get("to", ""),
            "subject": payload.get("subject", ""),
            "body": payload.get("text", ""),
            "html": payload.get("html", ""),
            "provider": self.name,
            "attachments": self.normalize_attachments(payload.get("attachments", [])),
        }

    def normalize_attachments(self, raw_attachments: list) -> list:
        normalized = []
        for att in raw_attachments:
            normalized.append({
                "filename": att.get("filename", "unnamed"),
                "content_b64": att.get("content", ""),
                "mime_type": att.get("type", "application/octet-stream"),
                "size": len(att.get("content", "")),
            })
        return normalized
