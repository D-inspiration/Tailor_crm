"""Polymorphic event hierarchy."""
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
        from services.fingerprint_service import FingerprintService
        from services.session_service import SessionService

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
        from services.session_service import SessionService

        SessionService.revoke(self.session_id)
        logger.info("LogoutEvent → session %s revoked", self.session_id[:8])
        return {"revoked": self.session_id}


class ActionEvent(BaseEvent):
    """
    Represents any CRM action.
    Updates risk, records event, increments subscription usage.
    """

    def process(self) -> Dict[str, Any]:
        from services.risk_service import RiskService
        from services.event_service import EventService
        from services.subscription_service import SubscriptionService
        from services.session_service import SessionService

        session = SessionService.get(self.session_id)
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
        from services.subscription_service import SubscriptionService
        from models.subscription import SUB_EXPIRED

        action = self.payload.get("action")
        if action == "upgrade":
            sub = SubscriptionService.update_plan(
                self.user_id, self.payload.get("plan", "pro")
            )
            logger.info("BillingEvent → user %s upgraded", self.user_id)
            return {"subscription": sub.to_dict()}
        elif action == "expire":
            sub = SubscriptionService.get_or_create(self.user_id)
            sub.status = SUB_EXPIRED
            from utils.extensions import db
            db.session.commit()
            return {"status": "expired"}
        return {"status": "no_action"}


class AbuseEvent(BaseEvent):
    """Explicit abuse signal — locks session, degrades fingerprint trust."""

    def process(self) -> Dict[str, Any]:
        from services.fingerprint_service import FingerprintService
        from services.session_service import SessionService

        session = SessionService.get(self.session_id)
        if session:
            session.lock()
            from utils.extensions import db
            db.session.commit()
            FingerprintService.degrade(session.device_fingerprint, amount=0.3)
            logger.warning("AbuseEvent → session %s locked", self.session_id[:8])
        return {"locked": self.session_id}
