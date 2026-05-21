"""
Mail service — orchestrates message lifecycle.
High-level operations for dashboard and automation.
"""

from typing import List, Optional
from ..repositories.message_repo import MessageRepository
from ..models.message import Message
from ..core.constants import MessageStatus


class MailService:
    """
    Encapsulated mail operations.
    Users interact through methods only — repository hidden internally.
    """

    def __init__(self):
        self._repo = MessageRepository()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def ingest(self, normalized_payload: dict) -> Message:
        """Create a Message from normalized provider output."""
        attachments_data = normalized_payload.pop("attachments", [])
        message = self._repo.create(**normalized_payload)
        # TODO: Persist attachments to storage and create Attachment records
        return message

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------
    def inbox(self, limit: int = 50, offset: int = 0) -> List[Message]:
        return self._repo.inbox(limit, offset)

    def search(self, query: str) -> List[Message]:
        return self._repo.search(query)

    def get(self, message_id: int) -> Optional[Message]:
        return self._repo.get_by_id(message_id)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    def mark_read(self, message_id: int) -> Message:
        msg = self._repo.get_by_id(message_id)
        if not msg:
            raise ValueError("Message not found")
        return msg.mark_read()

    def archive(self, message_id: int) -> Message:
        msg = self._repo.get_by_id(message_id)
        if not msg:
            raise ValueError("Message not found")
        return msg.archive()

    def mark_spam(self, message_id: int) -> Message:
        msg = self._repo.get_by_id(message_id)
        if not msg:
            raise ValueError("Message not found")
        return msg.mark_spam()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def stats(self) -> dict:
        return {
            "total": self._repo.count(),
            "unread": self._repo.unread_count(),
        }
