"""services/services.py — SessionService with auto-revoke"""
from datetime import timedelta
from typing import List, Optional
from models.models import Session, SESSION_ACTIVE, SESSION_REVOKED
from utils.hash import generate_session_id
from utils.time import utcnow
from utils.logger import get_logger
import store

logger = get_logger("SessionService")

_SESSION_TTL = timedelta(hours=24)


class SessionService:

    @staticmethod
    def create(user_id: int, fingerprint_hash: str,
               ip_address: str = None, user_agent: str = None) -> Session:
        
        active = SessionService.get_active_for_user(user_id)
        print(f"[DEBUG] User {user_id} has {len(active)} active sessions")
        
        from services.services import SubscriptionService
        sub = SubscriptionService.get_or_create(user_id)
        print(f"[DEBUG] Subscription: plan={sub.plan if sub else 'NONE'}, limits={sub.limits if sub else 'NONE'}")
        
        max_sessions = sub.limits.get('sessions', -1) if sub and sub.is_active() else -1
        print(f"[DEBUG] max_sessions={max_sessions}")
        
        if max_sessions != -1 and len(active) >= max_sessions:
            print(f"[DEBUG] SHOULD REVOKE — at limit")
            oldest = min(active, key=lambda s: s.created_at or utcnow())
            SessionService.revoke(oldest.id)
            print(f"[DEBUG] REVOKED {oldest.id[:8]}")
            active = SessionService.get_active_for_user(user_id)
        else:
            print(f"[DEBUG] NO REVOKE — max={max_sessions}, active={len(active)}")
        
        # Create new session (now under limit)
        session = Session(
            id=generate_session_id(),
            user_id=user_id,
            device_fingerprint=fingerprint_hash,
            status=SESSION_ACTIVE,
            created_at=utcnow(),
            expires_at=utcnow() + _SESSION_TTL,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        store.sessions.save(session)
        logger.info("Session created: %s for user %s", session.id, user_id)
        return session

    @staticmethod
    def get(session_id: str) -> Optional[Session]:
        return store.sessions.get(session_id)

    @staticmethod
    def validate(session_id: str) -> bool:
        session = store.sessions.get(session_id)
        if not session:
            return False
        return session.is_valid()

    @staticmethod
    def touch(session_id: str) -> None:
        session = store.sessions.get(session_id)
        if session:
            session.touch()
            store.sessions.save(session)

    @staticmethod
    def revoke(session_id: str) -> None:
        session = store.sessions.get(session_id)
        if session:
            session.revoke()
            store.sessions.save(session)
            logger.info("Session revoked: %s", session_id)

    @staticmethod
    def revoke_all_for_user(user_id: int) -> int:
        active = store.sessions.get_active_by_user(user_id)
        for s in active:
            s.revoke()
            store.sessions.save(s)
        logger.info("Revoked %d sessions for user %s", len(active), user_id)
        return len(active)

    @staticmethod
    def get_active_for_user(user_id: int) -> List[Session]:
        return store.sessions.get_active_by_user(user_id)


    