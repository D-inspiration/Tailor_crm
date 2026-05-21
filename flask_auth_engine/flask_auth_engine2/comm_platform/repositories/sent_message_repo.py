"""
Sent message repository with grouping/classification queries.
"""

from typing import List, Dict
from sqlalchemy import func, desc
from .base_repo import BaseRepository
from ..models.sent_message import SentMessage


class SentMessageRepository(BaseRepository[SentMessage]):

    def __init__(self):
        super().__init__(SentMessage)

    def by_sender(self, from_email: str, limit: int = 100) -> List[SentMessage]:
        return (
            db.session.query(SentMessage)
            .filter(func.lower(SentMessage.from_email) == from_email.lower().strip())
            .order_by(desc(SentMessage.sent_at))
            .limit(limit)
            .all()
        )

    def by_domain(self, domain: str, limit: int = 100) -> List[SentMessage]:
        return (
            db.session.query(SentMessage)
            .filter(SentMessage.from_email.like(f"%@{domain}"))
            .order_by(desc(SentMessage.sent_at))
            .limit(limit)
            .all()
        )

    def by_category(self, category: str, limit: int = 100) -> List[SentMessage]:
        return (
            db.session.query(SentMessage)
            .filter(SentMessage.category == category)
            .order_by(desc(SentMessage.sent_at))
            .limit(limit)
            .all()
        )

    def group_by_sender(self, limit: int = 50) -> List[Dict]:
        rows = (
            db.session.query(
                SentMessage.from_email,
                func.count(SentMessage.id).label("count"),
                func.max(SentMessage.sent_at).label("latest")
            )
            .group_by(func.lower(SentMessage.from_email))  # Case-insensitive
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )
        return [
            {"sender": r[0].strip().lower(), "count": r[1], "latest": r[2].isoformat() if r[2] else None}
            for r in rows
        ]

    def group_by_domain(self, limit: int = 50) -> List[Dict]:
        rows = (
            db.session.query(
                SentMessage.from_email,
                func.count(SentMessage.id).label("count"),
                func.max(SentMessage.sent_at).label("latest")
            )
            .group_by(SentMessage.from_email)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )
        domains: Dict[str, Dict] = {}
        for email, count, latest in rows:
            domain = email.split("@")[-1] if "@" in email else "unknown"
            if domain not in domains:
                domains[domain] = {"domain": domain, "count": 0, "senders": [], "latest": latest}
            domains[domain]["count"] += count
            domains[domain]["senders"].append(email)
            if latest and (not domains[domain]["latest"] or latest > domains[domain]["latest"]):
                domains[domain]["latest"] = latest

        result = list(domains.values())
        result.sort(key=lambda x: x["count"], reverse=True)
        for r in result:
            r["latest"] = r["latest"].isoformat() if r["latest"] else None
        return result

    def recent(self, limit: int = 50) -> List[SentMessage]:
        return (
            db.session.query(SentMessage)
            .order_by(desc(SentMessage.sent_at))
            .limit(limit)
            .all()
        )

    def stats(self) -> Dict:
        total = db.session.query(SentMessage).count()
        sent = db.session.query(SentMessage).filter(SentMessage.status == "sent").count()
        delivered = db.session.query(SentMessage).filter(SentMessage.status == "delivered").count()
        failed = db.session.query(SentMessage).filter(SentMessage.status == "failed").count()
        return {
            "total": total,
            "sent": sent,
            "delivered": delivered,
            "failed": failed,
            "senders": self.group_by_sender(10),
            "domains": self.group_by_domain(10),
        }


from utils.extensions import db
