"""Subscription / plan limit model."""
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.extensions import db
from utils.time import utcnow

SUB_ACTIVE = "active"
SUB_EXPIRED = "expired"
SUB_CANCELLED = "cancelled"
SUB_GRACE = "grace"  # 3-day buffer
SUB_LOCKED = "locked"

GRACE_PERIOD_DAYS = 3


DEFAULT_LIMITS = {
    "free": {
        "api_calls": 100,
        "events_per_day": 500,
        "sessions": 5,
        "customers": 20,
        "orders_per_month": 10,
        "storage_mb": 50,
        "staff_accounts": 1,
    },
    "starter": {
        "api_calls": 1000,
        "events_per_day": 5000,
        "sessions": 10,
        "customers": 150,
        "orders_per_month": 100,
        "storage_mb": 1024,
        "staff_accounts": 1,
    },
    "growth": {
        "api_calls": 10000,
        "events_per_day": 50000,
        "sessions": 20,
        "customers": 1000,
        "orders_per_month": -1,
        "storage_mb": 5120,
        "staff_accounts": 3,
    },
    "pro": {
        "api_calls": -1,
        "events_per_day": -1,
        "sessions": -1,
        "customers": -1,
        "orders_per_month": -1,
        "storage_mb": -1,
        "staff_accounts": -1,
    },
}


class Subscription(db.Model):
    """User subscription with plan limits."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    plan: Mapped[str] = mapped_column(String(16), default="free", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=SUB_ACTIVE, nullable=False)
    limits: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    usage: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.limits:
            self.limits = DEFAULT_LIMITS.get(self.plan, DEFAULT_LIMITS["free"]).copy()
        if not self.usage:
            self.usage = {k: 0 for k in self.limits}

    def is_active(self) -> bool:
        return self.status == SUB_ACTIVE

    def limit_exceeded(self, resource: str) -> bool:
        cap = self.limits.get(resource, 0)
        if cap == -1:
            return False
        return self.usage.get(resource, 0) >= cap

    def increment_usage(self, resource: str, amount: int = 1) -> None:
        self.usage[resource] = self.usage.get(resource, 0) + amount

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "plan": self.plan,
            "status": self.status,
            "limits": self.limits,
            "usage": self.usage,
        }
