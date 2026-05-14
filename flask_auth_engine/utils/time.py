"""utils/time.py"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(dt: datetime) -> bool:
    return utcnow() > dt


def seconds_until(dt: datetime) -> float:
    delta = dt - utcnow()
    return max(0.0, delta.total_seconds())
