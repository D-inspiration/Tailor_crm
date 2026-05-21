"""Event audit log model."""
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.extensions import db
from utils.time import utcnow

EVENT_LOGIN = "login"
EVENT_LOGOUT = "logout"
EVENT_ACTION = "action"
EVENT_BILLING = "billing"
EVENT_ABUSE = "abuse"
VALID_EVENT_TYPES = {EVENT_LOGIN, EVENT_LOGOUT, EVENT_ACTION, EVENT_BILLING, EVENT_ABUSE}


class Event(db.Model):
    """Polymorphic event record."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    session: Mapped["Session"] = relationship("Session", back_populates="events")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
