"""Session lifecycle service."""
from datetime import timedelta
from typing import List, Optional
from models.session import Session, SESSION_ACTIVE, SESSION_REVOKED
from models.subscription import Subscription
from utils.hash import generate_session_id
from utils.time import utcnow
from utils.logger import get_logger
from utils.extensions import db
from config import Config

logger = get_logger("SessionService")


class SessionService:
    """Manages session creation, validation, and revocation."""

    @staticmethod
    def create(
        user_id: int,
        fingerprint_hash: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Session:
        """Create a new session, auto-revoking oldest if over limit."""
        active = SessionService.get_active_for_user(user_id)
        sub = Subscription.query.filter_by(user_id=user_id).first()
        max_sessions = (
            sub.limits.get("sessions", -1)
            if sub and sub.is_active()
            else -1
        )

        if max_sessions != -1 and len(active) >= max_sessions:
            oldest = min(active, key=lambda s: s.created_at or utcnow())
            SessionService.revoke(oldest.id)
            logger.info(
                "Auto-revoked oldest session %s for user %s (limit: %d, had: %d)",
                oldest.id[:8], user_id, max_sessions, len(active),
            )
            active = SessionService.get_active_for_user(user_id)

        session = Session(
            id=generate_session_id(),
            user_id=user_id,
            device_fingerprint=fingerprint_hash,
            status=SESSION_ACTIVE,
            created_at=utcnow(),
            expires_at=utcnow() + Config.SESSION_TTL,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.session.add(session)
        db.session.commit()
        logger.info("Session created: %s for user %s", session.id, user_id)
        return session

    @staticmethod
    def get(session_id: str) -> Optional[Session]:
        return db.session.get(Session, session_id)

    @staticmethod
    def validate(session_id: str) -> bool:
        session = SessionService.get(session_id)
        if not session:
            return False
        return session.is_valid()

    @staticmethod
    def touch(session_id: str) -> None:
        session = SessionService.get(session_id)
        if session:
            session.touch()
            db.session.commit()

    @staticmethod
    def revoke(session_id: str) -> None:
        session = SessionService.get(session_id)
        if session:
            session.revoke()
            db.session.commit()
            logger.info("Session revoked: %s", session_id)

    @staticmethod
    def revoke_all_for_user(user_id: int) -> int:
        active = SessionService.get_active_for_user(user_id)
        for s in active:
            s.revoke()
        db.session.commit()
        logger.info("Revoked %d sessions for user %s", len(active), user_id)
        return len(active)

    @staticmethod
    def get_active_for_user(user_id: int) -> List[Session]:
        return (
            Session.query.filter_by(user_id=user_id, status=SESSION_ACTIVE)
            .all()
        )

    @staticmethod
    def enforce_plan_session_limit(user_id: int):
        sub = SubscriptionService.get_or_create(user_id)
        max_sessions = sub.limits.get("sessions", -1)
        
        if max_sessions == -1:
            return  # Unlimited
        
        active = SessionService.get_active_for_user(user_id)
        if len(active) > max_sessions:
            # Sort by last_activity, revoke oldest
            to_revoke = sorted(active, key=lambda s: s.last_activity_at)[:len(active) - max_sessions]
            for session in to_revoke:
                SessionService.revoke(session.id)
                EmailService.notify_session_revoked(user_id, session.id)
            
            return len(to_revoke)
        return 0
    
