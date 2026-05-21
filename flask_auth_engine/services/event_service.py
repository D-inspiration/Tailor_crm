"""Event recording service."""
from models.event import Event
from utils.logger import get_logger
from utils.extensions import db

logger = get_logger("EventService")


class EventService:
    """Records and retrieves audit events."""

    @staticmethod
    def record(
        session_id: str, user_id: int, event_type: str, payload: dict = None
    ) -> Event:
        event = Event(
            session_id=session_id,
            user_id=user_id,
            type=event_type,
            payload=payload or {},
        )
        db.session.add(event)
        db.session.commit()
        logger.debug("Event recorded: %s [session=%s]", event_type, session_id[:8])
        return event

    @staticmethod
    def get_session_history(session_id: str) -> list:
        events = Event.query.filter_by(session_id=session_id).order_by(Event.timestamp.desc()).all()
        return [e.to_dict() for e in events]
