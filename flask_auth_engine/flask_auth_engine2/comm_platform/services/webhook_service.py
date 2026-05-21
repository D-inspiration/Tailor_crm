"""
Webhook orchestration service.
Coordinates verification, logging, parsing, and downstream triggers.
"""

from typing import Dict, Any
from ..services.parser_service import ParserService
from ..services.mail_service import MailService
from ..services.notification_service import NotificationService
from ..models.webhook_log import WebhookLog
from ..core.config import CommConfig


class WebhookService:
    """
    Encapsulated webhook processing pipeline.
    Internal state (_log_id, _verified) protected.
    """

    def __init__(self):
        self._parser = ParserService()
        self._mail = MailService()
        self._notifier = NotificationService()
        self._log: WebhookLog | None = None

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    def process(self, payload, signature, headers):
    
        print("RAW PAYLOAD:", payload)
    
        provider_name = self._parser.detect_provider(headers)
    
        print("PROVIDER:", provider_name)
    
        self._log = WebhookLog(
            payload=str(payload),
            provider=provider_name,
            signature=signature,
        ).save()
    
        try:
            normalized = self._parser.parse(payload, signature, provider_name)
    
            print("NORMALIZED:", normalized)
    
        except Exception as e:
            print("PARSE ERROR:", str(e))
            return {"error": "parse_failed", "reason": str(e)}, 400
    
        message = self._mail.ingest(normalized)
    
        print("MESSAGE:", message)
    
        return {
            "status": "accepted",
            "message_id": getattr(message, "id", None),
            "provider": provider_name,
            "log_id": self._log.id,
        }
