"""Session model with hard boundary enforcement."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.extensions import db
from utils.time import utcnow, is_expired

SESSION_ACTIVE = "active"
SESSION_EXPIRED = "expired"
SESSION_REVOKED = "revoked"
SESSION_LOCKED = "locked"
VALID_STATUSES = {SESSION_ACTIVE, SESSION_EXPIRED, SESSION_REVOKED, SESSION_LOCKED}


class Session(db.Model):
    """Session entity — hard boundary anchor."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=SESSION_ACTIVE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    events: Mapped[list["Event"]] = relationship(
        "Event", back_populates="session", cascade="all, delete-orphan", lazy="dynamic"
    )
    risk_states: Mapped[list["RiskState"]] = relationship(
        "RiskState", back_populates="session", cascade="all, delete-orphan", lazy="dynamic"
    )

    def is_valid(self) -> bool:
        """Check if session is active and not expired."""
        if self.status != SESSION_ACTIVE:
            return False
        if self.expires_at and is_expired(self.expires_at):
            self.status = SESSION_EXPIRED
            return False
        return True

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = utcnow()

    def revoke(self) -> None:
        """Mark session as revoked."""
        self.status = SESSION_REVOKED

    def lock(self) -> None:
        """Mark session as locked (abuse)."""
        self.status = SESSION_LOCKED

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
