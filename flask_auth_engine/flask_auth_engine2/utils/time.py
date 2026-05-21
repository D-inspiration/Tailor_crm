"""Timezone-aware datetime utilities."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def is_expired(dt: datetime) -> bool:
    """Check if a datetime is in the past."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < utcnow()
