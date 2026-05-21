"""
Subscriber entity — subscription authority merged into comm platform.
"""

from typing import Optional, List
from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel
from ..core.constants import SubscriberStatus


class Subscriber(BaseModel):
    """
    Represents an audience member with subscription status.
    """

    __tablename__ = "comm_subscribers"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=SubscriberStatus.PENDING.value, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------
    def subscribe(self) -> "Subscriber":
        self.status = SubscriberStatus.ACTIVE.value
        return self.save()

    def unsubscribe(self) -> "Subscriber":
        self.status = SubscriberStatus.UNSUBSCRIBED.value
        return self.save()

    def change_plan(self, new_plan: str) -> "Subscriber":
        self.plan = new_plan
        return self.save()

    def add_tag(self, tag: str) -> "Subscriber":
        if tag not in (self.tags or []):
            self.tags = (self.tags or []) + [tag]
        return self.save()
