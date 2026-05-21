"""Hard session boundary enforcer."""
from services.session_service import SessionService
from utils.logger import get_logger

logger = get_logger("SessionGuard")


class SessionGuard:
    """
    Structural fix for event/identity collision.
    Events CANNOT cross session boundaries.
    """

    @staticmethod
    def validate(session_id: str, user_id: int = None) -> tuple[bool, str]:
        """
        Returns (is_valid, reason).
        Checks existence, active status, and user ownership.
        """
        session = SessionService.get(session_id)

        if not session:
            return False, "session_not_found"

        if not session.is_valid():
            return False, f"session_{session.status}"

        if user_id is not None and session.user_id != user_id:
            logger.error(
                "BOUNDARY VIOLATION: session %s belongs to user %s, "
                "request claims user %s",
                session_id[:8], session.user_id, user_id,
            )
            return False, "session_user_mismatch"

        return True, "ok"
