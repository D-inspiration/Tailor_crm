"""
Notification service — campaigns, alerts, and automation triggers.
MVP: simple logging. Future: email campaigns, Slack, webhooks.
"""

from ..models.message import Message
from ..models.subscriber import Subscriber


class NotificationService:
    """
    Encapsulated notification dispatcher.
    """

    def __init__(self):
        self._handlers = []

    def on_new_message(self, message: Message) -> None:
        """Hook called after every new message ingestion."""
        # MVP: log only. Future: trigger AI summary, autoresponder, CRM sync.
        pass

    def send_campaign(self, subscribers: list[Subscriber], subject: str, body: str) -> dict:
        """
        Future: bulk campaign dispatch.
        MVP: returns recipient count for dashboard preview.
        """
        return {"queued": len(subscribers), "status": "not_implemented"}
