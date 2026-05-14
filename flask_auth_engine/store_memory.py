"""
store.py — In-memory repository layer.
Each repository is a thin dict-backed store.
In production: replace with SQLAlchemy models or Redis-backed equivalents.
The service layer only imports from here — zero direct dict access elsewhere.
"""
from typing import Dict, List, Optional
from models.models import (
    User, DeviceFingerprint, Session, Event,
    RiskState, Subscription
)


class UserStore:
    def __init__(self):
        self._by_id: Dict[int, User] = {}
        self._by_email: Dict[str, int] = {}
        self._next_id = 1

    def save(self, user: User) -> User:
        if not user.id:
            user.id = self._next_id
            self._next_id += 1
        self._by_id[user.id] = user
        self._by_email[user.email.lower()] = user.id
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        uid = self._by_email.get(email.lower())
        return self._by_id.get(uid) if uid else None


class FingerprintStore:
    def __init__(self):
        self._store: Dict[str, DeviceFingerprint] = {}   # hash → fingerprint
        self._user_index: Dict[int, List[str]] = {}      # user_id → [hashes]
        self._next_id = 1

    def save(self, fp: DeviceFingerprint) -> DeviceFingerprint:
        if not fp.id:
            fp.id = self._next_id
            self._next_id += 1
        self._store[fp.fingerprint_hash] = fp
        self._user_index.setdefault(fp.user_id, [])
        if fp.fingerprint_hash not in self._user_index[fp.user_id]:
            self._user_index[fp.user_id].append(fp.fingerprint_hash)
        return fp

    def get(self, fp_hash: str) -> Optional[DeviceFingerprint]:
        return self._store.get(fp_hash)

    def get_by_user(self, user_id: int) -> List[DeviceFingerprint]:
        hashes = self._user_index.get(user_id, [])
        return [self._store[h] for h in hashes if h in self._store]

    def get_users_for_hash(self, fp_hash: str) -> List[int]:
        """Which users have this fingerprint? Used for reuse detection."""
        return [
            fp.user_id for fp in self._store.values()
            if fp.fingerprint_hash == fp_hash
        ]


class SessionStore:
    def __init__(self):
        self._store: Dict[str, Session] = {}
        self._user_index: Dict[int, List[str]] = {}

    def save(self, session: Session) -> Session:
        self._store[session.id] = session
        self._user_index.setdefault(session.user_id, [])
        if session.id not in self._user_index[session.user_id]:
            self._user_index[session.user_id].append(session.id)
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._store.get(session_id)

    def get_active_by_user(self, user_id: int) -> List[Session]:
        from models.models import SESSION_ACTIVE
        ids = self._user_index.get(user_id, [])
        return [
            self._store[sid] for sid in ids
            if sid in self._store and self._store[sid].status == SESSION_ACTIVE
        ]

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)


class EventStore:
    def __init__(self):
        self._store: List[Event] = []
        self._next_id = 1

    def save(self, event: Event) -> Event:
        event.id = self._next_id
        self._next_id += 1
        self._store.append(event)
        return event

    def get_by_session(self, session_id: str) -> List[Event]:
        return [e for e in self._store if e.session_id == session_id]

    def get_by_user(self, user_id: int) -> List[Event]:
        return [e for e in self._store if e.user_id == user_id]

    def recent_by_session(self, session_id: str, seconds: int = 10) -> List[Event]:
        from utils.time import utcnow
        from datetime import timedelta
        cutoff = utcnow() - timedelta(seconds=seconds)
        return [
            e for e in self._store
            if e.session_id == session_id and e.timestamp >= cutoff
        ]


class RiskStore:
    def __init__(self):
        self._store: Dict[str, RiskState] = {}  # session_id → state

    def save(self, state: RiskState) -> RiskState:
        self._store[state.session_id] = state
        return state

    def get(self, session_id: str) -> Optional[RiskState]:
        return self._store.get(session_id)


class SubscriptionStore:
    def __init__(self):
        self._store: Dict[int, Subscription] = {}  # user_id → subscription

    def save(self, sub: Subscription) -> Subscription:
        self._store[sub.user_id] = sub
        return sub

    def get(self, user_id: int) -> Optional[Subscription]:
        return self._store.get(user_id)


# ── Singleton stores (module-level, imported by services) ──────────────────
users = UserStore()
fingerprints = FingerprintStore()
sessions = SessionStore()
events = EventStore()
risks = RiskStore()
subscriptions = SubscriptionStore()
