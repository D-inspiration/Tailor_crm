"""services/session_service.py"""
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
        
        # Auto-revoke oldest session if at or over limit
        active = SessionService.get_active_for_user(user_id)
        sub = SubscriptionService.get_or_create(user_id)
        max_sessions = sub.limits.get('sessions', -1) if sub and sub.is_active() else -1
        
        if max_sessions != -1 and len(active) >= max_sessions:
            oldest = min(active, key=lambda s: s.created_at or utcnow())
            SessionService.revoke(oldest.id)
            logger.info(
                "Auto-revoked oldest session %s for user %s (limit: %d, had: %d)",
                oldest.id[:8], user_id, max_sessions, len(active)
            )
            active = SessionService.get_active_for_user(user_id)
        
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


"""services/fingerprint_service.py"""
from typing import Optional
from models.models import DeviceFingerprint
from utils.time import utcnow
from utils.logger import get_logger
import store

logger = get_logger("FingerprintService")

_TRUST_DECAY = 0.05
_REUSE_MAX_USERS = 1


class FingerprintService:

    @staticmethod
    def get_or_create(user_id: int, fp_hash: str) -> DeviceFingerprint:
        fp = store.fingerprints.get(fp_hash)
        if fp:
            if fp.user_id == user_id:
                fp.last_seen_at = utcnow()
                store.fingerprints.save(fp)
                return fp
            # Different user owns this fingerprint — create a new record
            logger.warning(
                "Fingerprint %s already owned by user %s, new entry for user %s",
                fp_hash[:8], fp.user_id, user_id
            )
        new_fp = DeviceFingerprint(id=0, user_id=user_id, fingerprint_hash=fp_hash)
        return store.fingerprints.save(new_fp)

    @staticmethod
    def degrade(fp_hash: str, amount: float = _TRUST_DECAY) -> None:
        fp = store.fingerprints.get(fp_hash)
        if fp:
            fp.degrade_trust(amount)
            store.fingerprints.save(fp)

    @staticmethod
    def is_reused_abnormally(fp_hash: str) -> bool:
        owners = store.fingerprints.get_users_for_hash(fp_hash)
        return len(set(owners)) > _REUSE_MAX_USERS

    @staticmethod
    def get_trust(fp_hash: str) -> float:
        fp = store.fingerprints.get(fp_hash)
        return fp.trust_score if fp else 0.5


"""services/risk_service.py"""
from models.models import RiskState, RISK_OK
from utils.time import utcnow
from utils.logger import get_logger
from services.services import FingerprintService
import store

logger = get_logger("RiskService")

_THROTTLE = 6
_BLOCK = 10
_BURST_WINDOW = 10   # seconds
_BURST_MAX = 20


class RiskService:

    @staticmethod
    def get_or_create(user_id: int, session_id: str) -> RiskState:
        state = store.risks.get(session_id)
        if not state:
            state = RiskState(user_id=user_id, session_id=session_id)
            store.risks.save(state)
        return state

    @staticmethod
    def evaluate(session_id: str, is_new_device: bool = False,
                 fp_hash: str = None) -> RiskState:
        session = store.sessions.get(session_id)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")

        state = RiskService.get_or_create(session.user_id, session_id)

        # New device signal
        if is_new_device:
            state.score += 2
            logger.debug("Risk +2: new device for session %s", session_id[:8])

        # Burst detection
        recent = store.events.recent_by_session(session_id, _BURST_WINDOW)
        if len(recent) >= _BURST_MAX:
            state.score += 3
            logger.warning("Risk +3: burst activity on session %s", session_id[:8])

        # Fingerprint reuse across users
        if fp_hash and FingerprintService.is_reused_abnormally(fp_hash):
            state.score += 4
            logger.warning("Risk +4: fingerprint reuse anomaly %s", fp_hash[:8])

        state.update_status(_THROTTLE, _BLOCK)
        store.risks.save(state)
        return state

    @staticmethod
    def get_status(session_id: str) -> str:
        state = store.risks.get(session_id)
        return state.status if state else RISK_OK

    @staticmethod
    def reset(session_id: str) -> None:
        state = store.risks.get(session_id)
        if state:
            state.score = 0
            state.status = RISK_OK
            store.risks.save(state)


"""services/subscription_service.py"""
from typing import Optional
from models.models import Subscription, SUB_ACTIVE
from utils.logger import get_logger
import store

logger = get_logger("SubscriptionService")


class SubscriptionService:

    @staticmethod
    def get_or_create(user_id: int, plan: str = "free") -> Subscription:
        sub = store.subscriptions.get(user_id)
        if not sub:
            sub = Subscription(user_id=user_id, plan=plan)
            store.subscriptions.save(sub)
        return sub

    @staticmethod
    def is_limit_exceeded(user_id: int, resource: str) -> bool:
        sub = store.subscriptions.get(user_id)
        if not sub or not sub.is_active():
            return True
        return sub.limit_exceeded(resource)

    @staticmethod
    def increment(user_id: int, resource: str, amount: int = 1) -> None:
        sub = SubscriptionService.get_or_create(user_id)
        sub.increment_usage(resource, amount)
        store.subscriptions.save(sub)

    @staticmethod
    def update_plan(user_id: int, new_plan: str) -> Subscription:
        sub = SubscriptionService.get_or_create(user_id)
        sub.plan = new_plan
        from models.models import DEFAULT_LIMITS
        sub.limits = DEFAULT_LIMITS.get(new_plan, DEFAULT_LIMITS["free"]).copy()
        store.subscriptions.save(sub)
        logger.info("User %s upgraded to plan: %s", user_id, new_plan)
        return sub


"""services/event_service.py"""
from models.models import Event
from utils.logger import get_logger
import store

logger = get_logger("EventService")


class EventService:

    @staticmethod
    def record(session_id: str, user_id: int, event_type: str,
               payload: dict = None) -> Event:
        event = Event(
            session_id=session_id,
            user_id=user_id,
            type=event_type,
            payload=payload or {},
        )
        store.events.save(event)
        logger.debug("Event recorded: %s [session=%s]", event_type, session_id[:8])
        return event

    @staticmethod
    def get_session_history(session_id: str) -> list:
        return [e.to_dict() for e in store.events.get_by_session(session_id)]

