"""Routes event_type strings to BaseEvent subclasses."""
from typing import Type
from engine.events import (
    BaseEvent,
    LoginEvent,
    LogoutEvent,
    ActionEvent,
    BillingEvent,
    AbuseEvent,
)

_REGISTRY: dict[str, Type[BaseEvent]] = {
    "login": LoginEvent,
    "logout": LogoutEvent,
    "action": ActionEvent,
    "billing": BillingEvent,
    "abuse": AbuseEvent,
}


class EventRouter:
    """Maps event type strings to event classes."""

    @staticmethod
    def resolve(event_type: str) -> Type[BaseEvent]:
        cls = _REGISTRY.get(event_type)
        if not cls:
            raise ValueError(f"Unknown event type: {event_type!r}")
        return cls

    @staticmethod
    def dispatch(
        event_type: str, session_id: str, user_id: int, payload: dict
    ) -> dict:
        cls = EventRouter.resolve(event_type)
        event = cls(session_id=session_id, user_id=user_id, payload=payload)
        return event.process()
