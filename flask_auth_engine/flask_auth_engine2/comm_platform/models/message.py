"""
Message entity — represents an inbound email.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Integer
#from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from .attachment import Attachment
from ..core.constants import MessageStatus, ProviderType


class Message(BaseModel):
    """
    Encapsulated email message.
    Internal spam score is protected; interact through methods/properties only.
    """

    __tablename__ = "comm_messages"

    # Identifiers
    sender = Column(String(255), nullable=False, index=True)
    recipient = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=True)

    # Content
    body = Column(Text, nullable=True)
    html = Column(Text, nullable=True)
    status = Column(String(20), default=MessageStatus.UNREAD.value, nullable=False)

    # Metadata
    _spam_score = Column("spam_score", Float, default=0.0, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    provider = Column(String(20), default=ProviderType.RESEND.value, nullable=False)

    # Relationships
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", back_populates="message", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------
    # Encapsulation: internal state protected
    # ------------------------------------------------------------------
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._verified = False  # Runtime-only, not persisted

    # ------------------------------------------------------------------
    # Properties (computed values)
    # ------------------------------------------------------------------
    @property
    def preview(self) -> str:
        """First N characters of body for list views."""
        from ..core.config import CommConfig
        length = CommConfig.get("COMM_PREVIEW_LENGTH")
        text = (self.body or "")[:length]
        return text + "..." if len(self.body or "") > length else text

    @property
    def is_spam(self) -> bool:
        from ..core.config import CommConfig
        return self._spam_score > CommConfig.get("COMM_SPAM_THRESHOLD")

    @property
    def attachment_count(self) -> int:
        return len(self.attachments)

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------
    def mark_read(self) -> "Message":
        self.status = MessageStatus.READ.value
        return self.save()

    def archive(self) -> "Message":
        self.status = MessageStatus.ARCHIVED.value
        return self.save()

    def mark_spam(self) -> "Message":
        self.status = MessageStatus.SPAM.value
        return self.save()

    def extract_links(self) -> List[str]:
        """Parse HTML/body for URLs."""
        import re
        text = self.html or self.body or ""
        return re.findall(r"https?://[^\s<<>'\"]+", text)


    def summarize(self) -> str:
        """
        Placeholder for AI summarization.
        Future: integrate with Gemini/Claude API.
        """
        return self.preview  # MVP fallback
