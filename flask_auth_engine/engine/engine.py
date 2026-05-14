"""
engine/events.py — Polymorphic event hierarchy.
Each event type owns its own process() logic.
Same interface, different behaviour.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from utils.logger import get_logger

logger = get_logger("EventEngine")


class BaseEvent(ABC):
    """Abstract base — enforces process() contract on all event types."""

    def __init__(self, session_id: str, user_id: int, payload: Dict[str, Any]):
        self.session_id = session_id
        self.user_id = user_id
        self.payload = payload

    @abstractmethod
    def process(self) -> Dict[str, Any]:
        raise NotImplementedError


class LoginEvent(BaseEvent):
    """Creates session. Called once per successful auth."""

    def process(self) -> Dict[str, Any]:
        from services.services import SessionService, FingerprintService
        fp_hash = self.payload.get("fingerprint_hash", "unknown")
        FingerprintService.get_or_create(self.user_id, fp_hash)
        session = SessionService.create(
            user_id=self.user_id,
            fingerprint_hash=fp_hash,
            ip_address=self.payload.get("ip_address"),
            user_agent=self.payload.get("user_agent"),
        )
        logger.info("LoginEvent → session %s created", session.id[:8])
        return {"session": session.to_dict()}


class LogoutEvent(BaseEvent):
    """Revokes the current session."""

    def process(self) -> Dict[str, Any]:
        from services.services import SessionService
        SessionService.revoke(self.session_id)
        logger.info("LogoutEvent → session %s revoked", self.session_id[:8])
        return {"revoked": self.session_id}


class ActionEvent(BaseEvent):
    """
    Represents any CRM action (create record, update field, run report, etc.).
    Updates risk, records event, increments subscription usage.
    """

    def process(self) -> Dict[str, Any]:
        from services.services import RiskService, EventService, SubscriptionService
        session = __import__("store").sessions.get(self.session_id)
        fp_hash = session.device_fingerprint if session else None

        risk = RiskService.evaluate(
            session_id=self.session_id,
            is_new_device=self.payload.get("is_new_device", False),
            fp_hash=fp_hash,
        )
        event = EventService.record(
            session_id=self.session_id,
            user_id=self.user_id,
            event_type="action",
            payload=self.payload,
        )
        SubscriptionService.increment(self.user_id, "events_per_day")
        SubscriptionService.increment(self.user_id, "api_calls")
        logger.debug("ActionEvent processed, risk=%s", risk.status)
        return {"event_id": event.id, "risk_status": risk.status}


class BillingEvent(BaseEvent):
    """Updates subscription state — plan changes, renewals, expirations."""

    def process(self) -> Dict[str, Any]:
        from services.services import SubscriptionService
        action = self.payload.get("action")
        if action == "upgrade":
            sub = SubscriptionService.update_plan(
                self.user_id, self.payload.get("plan", "pro")
            )
            logger.info("BillingEvent → user %s upgraded", self.user_id)
            return {"subscription": sub.to_dict()}
        elif action == "expire":
            sub = __import__("store").subscriptions.get(self.user_id)
            if sub:
                from models.models import SUB_EXPIRED
                sub.status = SUB_EXPIRED
                __import__("store").subscriptions.save(sub)
            return {"status": "expired"}
        return {"status": "no_action"}


class AbuseEvent(BaseEvent):
    """Explicit abuse signal — locks session, degrades fingerprint trust."""

    def process(self) -> Dict[str, Any]:
        from services.services import FingerprintService
        import store as _store
        session = _store.sessions.get(self.session_id)
        if session:
            session.lock()
            _store.sessions.save(session)
            FingerprintService.degrade(session.device_fingerprint, amount=0.3)
        logger.warning(
            "AbuseEvent → session %s locked", self.session_id[:8]
        )
        return {"locked": self.session_id}


"""
engine/event_router.py — Routes event_type strings to BaseEvent subclasses.
Single responsibility: type → class mapping, nothing more.
"""
from typing import Type
from engine.engine import (
    BaseEvent, LoginEvent, LogoutEvent,
    ActionEvent, BillingEvent, AbuseEvent
)

_REGISTRY: dict[str, Type[BaseEvent]] = {
    "login":   LoginEvent,
    "logout":  LogoutEvent,
    "action":  ActionEvent,
    "billing": BillingEvent,
    "abuse":   AbuseEvent,
}


class EventRouter:

    @staticmethod
    def resolve(event_type: str) -> Type[BaseEvent]:
        cls = _REGISTRY.get(event_type)
        if not cls:
            raise ValueError(f"Unknown event type: {event_type!r}")
        return cls

    @staticmethod
    def dispatch(event_type: str, session_id: str,
                 user_id: int, payload: dict) -> dict:
        cls = EventRouter.resolve(event_type)
        event = cls(session_id=session_id, user_id=user_id, payload=payload)
        return event.process()


"""
engine/session_guard.py — Hard session boundary enforcer.
This is the structural fix for event/identity collision.
Events CANNOT cross session boundaries. Period.
"""
from utils.logger import get_logger

logger = get_logger("SessionGuard")


class SessionGuard:

    @staticmethod
    def validate(session_id: str, user_id: int = None) -> tuple[bool, str]:
        """
        Returns (is_valid: bool, reason: str).
        Checks:
          1. Session exists
          2. Session is active / not expired
          3. If user_id provided, session belongs to that user (hard boundary)
        """
        import store
        session = store.sessions.get(session_id)

        if not session:
            return False, "session_not_found"

        if not session.is_valid():
            return False, f"session_{session.status}"

        if user_id is not None and session.user_id != user_id:
            logger.error(
                "BOUNDARY VIOLATION: session %s belongs to user %s, "
                "request claims user %s",
                session_id[:8], session.user_id, user_id
            )
            return False, "session_user_mismatch"

        return True, "ok"


"""
engine/risk_engine.py — Pure risk evaluation, no side effects.
Called by RiskService; isolated so scoring logic can evolve independently.
"""
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger("RiskEngine")


@dataclass
class RiskSignals:
    is_new_device: bool = False
    is_burst: bool = False
    fingerprint_reused: bool = False
    low_trust_fingerprint: bool = False
    explicit_abuse: bool = False


class RiskEngine:

    WEIGHTS = {
        "is_new_device":          2,
        "is_burst":               3,
        "fingerprint_reused":     4,
        "low_trust_fingerprint":  2,
        "explicit_abuse":         5,
    }

    @staticmethod
    def score(signals: RiskSignals) -> int:
        total = 0
        for field, weight in RiskEngine.WEIGHTS.items():
            if getattr(signals, field, False):
                total += weight
                logger.debug("Risk +%d: %s", weight, field)
        return total


"""
engine/subscription_guard.py — Plan limit enforcement.
Returns allow/deny based on current usage vs plan caps.
"""
from utils.logger import get_logger

logger = get_logger("SubscriptionGuard")


class SubscriptionGuard:

    @staticmethod
    def validate(user_id: int, resource: str) -> tuple[bool, str]:
        import store
        sub = store.subscriptions.get(user_id)
        if not sub:
            return False, "no_subscription"
        if not sub.is_active():
            return False, "subscription_expired"
        if sub.limit_exceeded(resource):
            logger.warning(
                "Limit exceeded for user %s resource=%s plan=%s",
                user_id, resource, sub.plan
            )
            return False, f"limit_exceeded:{resource}"
        return True, "ok"
