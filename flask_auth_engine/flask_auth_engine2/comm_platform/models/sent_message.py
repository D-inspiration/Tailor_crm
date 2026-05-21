"""
Sent message entity — tracks outbound emails via Resend API.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class SentMessage(BaseModel):
    """
    Represents an email sent through the platform.
    Used for classification, analytics, and sender reputation.
    """

    __tablename__ = "comm_sent_messages"

    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    from_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    resend_message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    @property
    def sender_domain(self) -> str:
        return self.from_email.split("@")[-1] if "@" in self.from_email else ""

    @property
    def sender_label(self) -> str:
        if self.from_name:
            return f"{self.from_name} <{self.from_email}>"
        return self.from_email

    def mark_sent(self, resend_id: str) -> "SentMessage":
        self.resend_message_id = resend_id
        self.status = "sent"
        return self.save()

    def mark_delivered(self) -> "SentMessage":
        self.status = "delivered"
        self.delivered_at = datetime.utcnow()
        return self.save()

    def mark_failed(self, reason: str = "") -> "SentMessage":
        self.status = "failed"
        if reason:
            self.tags = (self.tags or []) + [f"error:{reason}"]
        return self.save()
        