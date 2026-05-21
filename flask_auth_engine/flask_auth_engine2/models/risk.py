"""Risk state model."""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.extensions import db
from utils.time import utcnow

RISK_OK = "ok"
RISK_WARNING = "warning"
RISK_THROTTLED = "throttled"
RISK_BLOCKED = "blocked"


class RiskState(db.Model):
    """Per-session risk scoring state."""

    __tablename__ = "risk_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=RISK_OK, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    burst_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="risk_states")

    def update_status(self, throttle_threshold: int, block_threshold: int) -> None:
        """Recalculate status based on current score."""
        if self.score >= block_threshold:
            self.status = RISK_BLOCKED
        elif self.score >= throttle_threshold:
            self.status = RISK_THROTTLED
        elif self.score >= throttle_threshold // 2:
            self.status = RISK_WARNING
        else:
            self.status = RISK_OK
        self.last_updated = utcnow()

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "score": self.score,
            "status": self.status,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
