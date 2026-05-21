"""Device fingerprint model."""
from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from utils.extensions import db
from utils.time import utcnow


class DeviceFingerprint(db.Model):
    """Device fingerprint — soft signal only, never a join key."""

    __tablename__ = "device_fingerprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fingerprint_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    trust_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_fp_hash_user", "fingerprint_hash", "user_id", unique=True),
    )

    def degrade_trust(self, amount: float = 0.05) -> None:
        """Reduce trust score."""
        self.trust_score = max(0.0, self.trust_score - amount)

    def is_trusted(self, threshold: float = 0.5) -> bool:
        """Check if trust score meets threshold."""
        return self.trust_score >= threshold

    def to_dict(self) -> dict:
        return {
            "fingerprint_hash": self.fingerprint_hash,
            "trust_score": self.trust_score,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }
