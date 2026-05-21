"""
Webhook audit trail.
Every inbound webhook is logged for debugging and replay.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Text, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class WebhookLog(BaseModel):
    """Immutable log of raw webhook payloads."""

    __tablename__ = "comm_webhook_logs"

    payload: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------
    def mark_verified(self) -> "WebhookLog":
        self.verified = True
        return self.save()
