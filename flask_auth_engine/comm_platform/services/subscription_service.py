"""
Subscription authority service.
Manages audience lifecycle: opt-in, segmentation, campaigns.
"""

from typing import List, Optional
from ..repositories.subscriber_repo import SubscriberRepository
from ..models.subscriber import Subscriber
from ..core.constants import SubscriberStatus


class SubscriptionService:
    """
    Encapsulated subscription management.
    """

    def __init__(self):
        self._repo = SubscriberRepository()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, email: str, source: str = "web", tags: list = None, plan: str = "free") -> Subscriber:
        """Idempotent registration — returns existing if already present."""
        existing = self._repo.get_by_email(email)
        if existing:
            return existing
        return self._repo.create(
            email=email,
            source=source,
            tags=tags or [],
            plan=plan,
            status=SubscriberStatus.PENDING.value,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def confirm(self, email: str) -> Subscriber:
        sub = self._repo.get_by_email(email)
        if not sub:
            raise ValueError("Subscriber not found")
        return sub.subscribe()

    def unsubscribe(self, email: str) -> Subscriber:
        sub = self._repo.get_by_email(email)
        if not sub:
            raise ValueError("Subscriber not found")
        return sub.unsubscribe()

    def change_plan(self, email: str, new_plan: str) -> Subscriber:
        sub = self._repo.get_by_email(email)
        if not sub:
            raise ValueError("Subscriber not found")
        return sub.change_plan(new_plan)

    def tag(self, email: str, tag: str) -> Subscriber:
        sub = self._repo.get_by_email(email)
        if not sub:
            raise ValueError("Subscriber not found")
        return sub.add_tag(tag)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def audience(self, tag: str = None, plan: str = None, status: SubscriberStatus = None) -> List[Subscriber]:
        if tag:
            return self._repo.by_tag(tag)
        if plan:
            return self._repo.by_plan(plan)
        if status:
            return self._repo.by_status(status)
        return self._repo.get_all()

    def stats(self) -> dict:
        return {
            "total": self._repo.count(),
            "active": self._repo.active_count(),
            "segments": self._repo.tag_counts(),
        }
