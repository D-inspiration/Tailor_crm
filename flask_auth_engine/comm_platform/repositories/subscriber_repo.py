"""
Subscriber-specific queries with segmentation support.
"""

from typing import List, Optional
from sqlalchemy import func
from .base_repo import BaseRepository
from ..models.subscriber import Subscriber
from ..core.constants import SubscriberStatus


class SubscriberRepository(BaseRepository[Subscriber]):
    """Encapsulated subscriber data access."""

    def __init__(self):
        super().__init__(Subscriber)

    def get_by_email(self, email: str) -> Optional[Subscriber]:
        return db.session.query(Subscriber).filter(Subscriber.email == email).first()

    def by_status(self, status: SubscriberStatus) -> List[Subscriber]:
        return (
            db.session.query(Subscriber)
            .filter(Subscriber.status == status.value)
            .all()
        )

    def by_tag(self, tag: str) -> List[Subscriber]:
        """JSON containment query for audience segmentation."""
        return (
            db.session.query(Subscriber)
            .filter(Subscriber.tags.contains([tag]))
            .all()
        )

    def by_plan(self, plan: str) -> List[Subscriber]:
        return (
            db.session.query(Subscriber)
            .filter(Subscriber.plan == plan)
            .all()
        )

    def active_count(self) -> int:
        return (
            db.session.query(Subscriber)
            .filter(Subscriber.status == SubscriberStatus.ACTIVE.value)
            .count()
        )

    def tag_counts(self) -> dict:
        """Aggregate count per tag for dashboard analytics."""
        rows = db.session.query(Subscriber.tags).all()
        counts: dict = {}
        for (tags,) in rows:
            if tags:
                for tag in tags:
                    counts[tag] = counts.get(tag, 0) + 1
        return counts

from utils.extensions import db
