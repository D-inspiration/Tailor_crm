"""
store_sqlite.py — SQLite-backed repository layer.
Drop-in replacement for store.py. Same interface, persistent storage.
"""
import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime
from models.models import (
    User, DeviceFingerprint, Session, Event,
    RiskState, Subscription,
    SESSION_ACTIVE, SESSION_REVOKED, SESSION_EXPIRED,
    SUB_ACTIVE, SUB_EXPIRED, SUB_CANCELLED,
    RISK_OK, RISK_THROTTLED, RISK_BLOCKED
)

DB_PATH = "sbeae.db"


def _init_db():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            phone TEXT,
            password_hash TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            device_fingerprint TEXT,
            status TEXT,
            created_at TEXT,
            expires_at TEXT,
            last_activity_at TEXT,
            ip_address TEXT,
            user_agent TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            plan TEXT,
            status TEXT,
            limits TEXT,
            usage TEXT,
            created_at TEXT,
            expires_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_id INTEGER,
            type TEXT,
            payload TEXT,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


class UserStore:
    def __init__(self):
        _init_db()

    def save(self, user: User) -> User:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            '''INSERT OR REPLACE INTO users 
               (id, email, phone, password_hash, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user.id, user.email, user.phone, user.password_hash,
             1 if user.is_active else 0, user.created_at.isoformat() if user.created_at else None)
        )
        conn.commit()
        if not user.id:
            user.id = c.lastrowid
        conn.close()
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE id=?', (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return User(
                id=row[0], email=row[1], phone=row[2],
                password_hash=row[3], is_active=bool(row[4]),
                created_at=datetime.fromisoformat(row[5]) if row[5] else None
            )
        return None

    def get_by_email(self, email: str) -> Optional[User]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email=?', (email.lower(),))
        row = c.fetchone()
        conn.close()
        if row:
            return User(
                id=row[0], email=row[1], phone=row[2],
                password_hash=row[3], is_active=bool(row[4]),
                created_at=datetime.fromisoformat(row[5]) if row[5] else None
            )
        return None


class SessionStore:
    def __init__(self):
        _init_db()

    def save(self, session: Session) -> Session:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            '''INSERT OR REPLACE INTO sessions 
               (id, user_id, device_fingerprint, status, created_at, 
                expires_at, last_activity_at, ip_address, user_agent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (session.id, session.user_id, session.device_fingerprint,
             session.status, 
             session.created_at.isoformat() if session.created_at else None,
             session.expires_at.isoformat() if session.expires_at else None,
             session.last_activity_at.isoformat() if session.last_activity_at else None,
             session.ip_address, session.user_agent)
        )
        conn.commit()
        conn.close()
        return session

    def get(self, session_id: str) -> Optional[Session]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM sessions WHERE id=?', (session_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return Session(
                id=row[0], user_id=row[1], device_fingerprint=row[2],
                status=row[3],
                created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                expires_at=datetime.fromisoformat(row[5]) if row[5] else None,
                last_activity_at=datetime.fromisoformat(row[6]) if row[6] else None,
                ip_address=row[7], user_agent=row[8]
            )
        return None

    def get_active_by_user(self, user_id: int) -> List[Session]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM sessions WHERE user_id=? AND status=?', 
                  (user_id, SESSION_ACTIVE))
        rows = c.fetchall()
        conn.close()
        return [
            Session(
                id=r[0], user_id=r[1], device_fingerprint=r[2],
                status=r[3],
                created_at=datetime.fromisoformat(r[4]) if r[4] else None,
                expires_at=datetime.fromisoformat(r[5]) if r[5] else None,
                last_activity_at=datetime.fromisoformat(r[6]) if r[6] else None,
                ip_address=r[7], user_agent=r[8]
            ) for r in rows
        ]

    def delete(self, session_id: str) -> None:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM sessions WHERE id=?', (session_id,))
        conn.commit()
        conn.close()


class SubscriptionStore:
    def __init__(self):
        _init_db()

    def save(self, sub: Subscription) -> Subscription:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            '''INSERT OR REPLACE INTO subscriptions 
               (user_id, plan, status, limits, usage, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (sub.user_id, sub.plan, sub.status,
             json.dumps(sub.limits), json.dumps(sub.usage),
             sub.created_at.isoformat() if sub.created_at else None,
             sub.expires_at.isoformat() if sub.expires_at else None)
        )
        conn.commit()
        conn.close()
        return sub

    def get(self, user_id: int) -> Optional[Subscription]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM subscriptions WHERE user_id=?', (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return Subscription(
                user_id=row[0], plan=row[1], status=row[2],
                limits=json.loads(row[3]) if row[3] else {},
                usage=json.loads(row[4]) if row[4] else {},
                created_at=datetime.fromisoformat(row[5]) if row[5] else None,
                expires_at=datetime.fromisoformat(row[6]) if row[6] else None
            )
        return None


# Simple in-memory stores for non-critical data (events, fingerprints, risk)
class FingerprintStore:
    def __init__(self):
        self._store: Dict[str, DeviceFingerprint] = {}
        self._user_index: Dict[int, List[str]] = {}
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

    def get_users_for_hash(self, fp_hash: str) -> List[int]:
        return [
            fp.user_id for fp in self._store.values()
            if fp.fingerprint_hash == fp_hash
        ]


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
        self._store: Dict[str, RiskState] = {}

    def save(self, state: RiskState) -> RiskState:
        self._store[state.session_id] = state
        return state

    def get(self, session_id: str) -> Optional[RiskState]:
        return self._store.get(session_id)


# ── Singleton stores ──────────────────
users = UserStore()
fingerprints = FingerprintStore()
sessions = SessionStore()
events = EventStore()
risks = RiskStore()
subscriptions = SubscriptionStore()

