"""models/user.py"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from utils.hash import sha256
from utils.time import utcnow


@dataclass
class User:
    
    email: str
    phone: str
    password_hash: str
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)
    id: int = None

    def check_password(self, raw_password: str) -> bool:
        return self.password_hash == sha256(raw_password)

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
        }


"""models/fingerprint.py"""
from dataclasses import dataclass, field
from datetime import datetime
from utils.time import utcnow


@dataclass
class DeviceFingerprint:
    id: int
    user_id: int
    fingerprint_hash: str
    trust_score: float = 1.0          # 0.0 = untrusted → 1.0 = fully trusted
    first_seen_at: datetime = field(default_factory=utcnow)
    last_seen_at: datetime = field(default_factory=utcnow)

    def degrade_trust(self, amount: float = 0.05) -> None:
        self.trust_score = max(0.0, self.trust_score - amount)

    def is_trusted(self, threshold: float = 0.5) -> bool:
        return self.trust_score >= threshold

    def to_dict(self) -> dict:
        return {
            "fingerprint_hash": self.fingerprint_hash,
            "trust_score": self.trust_score,
            "last_seen_at": self.last_seen_at.isoformat(),
        }


"""models/session.py"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from utils.time import utcnow, is_expired

SESSION_ACTIVE = "active"
SESSION_EXPIRED = "expired"
SESSION_REVOKED = "revoked"
SESSION_LOCKED = "locked"

VALID_STATUSES = {SESSION_ACTIVE, SESSION_EXPIRED, SESSION_REVOKED, SESSION_LOCKED}


@dataclass
class Session:
    id: str                             # Hard boundary anchor
    user_id: int
    device_fingerprint: str             # Soft signal only
    status: str = SESSION_ACTIVE
    created_at: datetime = field(default_factory=utcnow)
    expires_at: datetime = field(default=None)
    last_activity_at: datetime = field(default_factory=utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def is_valid(self) -> bool:
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
        self.status = SESSION_REVOKED

    def lock(self) -> None:
        self.status = SESSION_LOCKED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


"""models/event.py"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from utils.time import utcnow

EVENT_LOGIN = "login"
EVENT_LOGOUT = "logout"
EVENT_ACTION = "action"
EVENT_BILLING = "billing"
EVENT_ABUSE = "abuse"

VALID_EVENT_TYPES = {EVENT_LOGIN, EVENT_LOGOUT, EVENT_ACTION, EVENT_BILLING, EVENT_ABUSE}


@dataclass
class Event:
    session_id: str
    user_id: int
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utcnow)
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }


"""models/risk.py"""
from dataclasses import dataclass, field
from datetime import datetime
from utils.time import utcnow

RISK_OK = "ok"
RISK_WARNING = "warning"
RISK_THROTTLED = "throttled"
RISK_BLOCKED = "blocked"


@dataclass
class RiskState:
    user_id: int
    session_id: str
    score: int = 0
    status: str = RISK_OK
    last_updated: datetime = field(default_factory=utcnow)
    event_count: int = 0               # For burst detection
    burst_window_start: datetime = field(default_factory=utcnow)

    def update_status(self, throttle_threshold: int, block_threshold: int) -> None:
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
            "last_updated": self.last_updated.isoformat(),
        }


"""models/subscription.py"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from utils.time import utcnow

SUB_ACTIVE = "active"
SUB_EXPIRED = "expired"
SUB_CANCELLED = "cancelled"


DEFAULT_LIMITS = {
    "free": {
        "api_calls": 100,
        "events_per_day": 500,
        "sessions": 5,              # 5 devices/tabs
        "customers": 20,
        "orders_per_month": 10,
        "storage_mb": 50,
        "staff_accounts": 1,
    },
    "starter": {
        "api_calls": 1000,
        "events_per_day": 5000,
        "sessions": 10,             # Personal + work + spare
        "customers": 150,
        "orders_per_month": 100,
        "storage_mb": 1024,
        "staff_accounts": 1,
    },
    "growth": {
        "api_calls": 10000,
        "events_per_day": 50000,
        "sessions": 20,             # Small team
        "customers": 1000,
        "orders_per_month": -1,
        "storage_mb": 5120,
        "staff_accounts": 3,        # Allow 3 staff
    },
    "pro": {
        "api_calls": -1,
        "events_per_day": -1,
        "sessions": -1,             # Unlimited
        "customers": -1,
        "orders_per_month": -1,
        "storage_mb": -1,
        "staff_accounts": -1,       # Unlimited team
    },
}


from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional


SUB_ACTIVE = "active"
SUB_CANCELLED = "cancelled"
SUB_SUSPENDED = "suspended"


def utcnow():
    return datetime.now(timezone.utc)


@dataclass
class Subscription:
    user_id: int
    plan: str = "free"
    status: str = SUB_ACTIVE

    limits: Dict[str, Any] = field(default_factory=dict)
    usage: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=utcnow)
    expires_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # -------------------------
    # CORE STATE RULES
    # -------------------------
    def limit_exceeded(self, resource: str) -> tuple[bool, str]:
        """
        Returns (is_exceeded, reason)
        """

        limit = self.limits.get(resource)
        used = self.usage.get(resource, 0)

        if limit is None:
            return False, "no_limit"

        if used >= limit:
            return True, f"limit_reached: {used}/{limit}"

        return False, "ok"

    def is_expired(self) -> bool:
        """
        Expiry is the ONLY hard cutoff rule.
        Free plans never expire.
        """
        if self.plan == "free":
            return False

        if not self.expires_at:
            return False

        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        return utcnow() > expiry

    def is_cancelled(self) -> bool:
        return self.status == SUB_CANCELLED

    def is_suspended(self) -> bool:
        return self.status == SUB_SUSPENDED

    def is_active(self) -> bool:
        """
        Active means:
        - not suspended
        - not expired
        """
        if self.is_suspended():
            return False

        if self.is_expired():
            return False

        return True

    # -------------------------
    # GRACE LOGIC
    # -------------------------

    def is_grace_period(self) -> bool:
        """
        Cancelled but still within paid time window.
        """
        if not self.is_cancelled():
            return False

        if not self.expires_at:
            return False

        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        return utcnow() < expiry
        
    def days_remaining(self) -> int:
        """
        Returns remaining days until expiry.
        Free plan = infinite (-1)
        """
        if not self.expires_at:
            return -1  # free plan or no expiry
    
        now = datetime.now(timezone.utc)
    
        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
    
        delta = expiry - now
    
        return max(delta.days, 0)

    # -------------------------
    # ACTIONS
    # -------------------------

    def cancel(self) -> None:
        """
        Marks cancellation but does NOT revoke access immediately.
        """
        self.status = SUB_CANCELLED
        self.cancelled_at = utcnow()

    def suspend(self) -> None:
        """
        Hard block access immediately.
        """
        self.status = SUB_SUSPENDED

    def restore(self) -> None:
        """
        Restore to active state (used after payment or admin action).
        """
        self.status = SUB_ACTIVE
        self.cancelled_at = None

    def downgrade_to_free(self) -> None:
        """
        Reset to free tier safely.
        """
        self.plan = "free"
        self.status = SUB_ACTIVE
        self.expires_at = None
        self.cancelled_at = None

        # optional but safe reset
        self.limits = {
            "api_calls": 100,
            "customers": 20,
            "events_per_day": 500,
            "orders_per_month": 10,
            "sessions": 5,
            "staff_accounts": 1,
            "storage_mb": 50
        }

