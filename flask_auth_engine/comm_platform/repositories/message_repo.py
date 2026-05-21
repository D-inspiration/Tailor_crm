"""
Message-specific queries.
"""

from typing import List, Optional
from sqlalchemy import or_, desc
from .base_repo import BaseRepository
from ..models.message import Message
from ..core.constants import MessageStatus


class MessageRepository(BaseRepository[Message]):
    """Encapsulated message data access."""

    def __init__(self):
        super().__init__(Message)

    def search(self, query: str, limit: int = 50) -> List[Message]:
        """Full-text search across sender, recipient, subject, body."""
        pattern = f"%{query}%"
        return (
            db.session.query(Message)
            .filter(
                or_(
                    Message.sender.ilike(pattern),
                    Message.recipient.ilike(pattern),
                    Message.subject.ilike(pattern),
                    Message.body.ilike(pattern),
                )
            )
            .order_by(desc(Message.received_at))
            .limit(limit)
            .all()
        )

    def by_status(self, status: MessageStatus, limit: int = 100) -> List[Message]:
        return (
            db.session.query(Message)
            .filter(Message.status == status.value)
            .order_by(desc(Message.received_at))
            .limit(limit)
            .all()
        )

    def inbox(self, limit: int = 50, offset: int = 0) -> List[Message]:
        """Unread + read messages (not archived/deleted)."""
        return (
            db.session.query(Message)
            .filter(
                Message.status.in_([
                    MessageStatus.UNREAD.value,
                    MessageStatus.READ.value,
                ])
            )
            .order_by(desc(Message.received_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def unread_count(self) -> int:
        return (
            db.session.query(Message)
            .filter(Message.status == MessageStatus.UNREAD.value)
            .count()
        )

    def by_sender(self, sender: str) -> List[Message]:
        return (
            db.session.query(Message)
            .filter(Message.sender == sender)
            .order_by(desc(Message.received_at))
            .all()
        )

# Lazy import to avoid circular dependency at module load
from utils.extensions import db
