"""Risk evaluation and persistence service."""
from datetime import timedelta
from typing import Optional
from models.risk import RiskState, RISK_OK
from models.event import Event
from utils.time import utcnow
from utils.logger import get_logger
from utils.extensions import db
from config import Config
from services.fingerprint_service import FingerprintService

logger = get_logger("RiskService")


class RiskService:
    """Manages risk state per session."""

    @staticmethod
    def get_or_create(user_id: int, session_id: str) -> RiskState:
        state = RiskState.query.filter_by(session_id=session_id).first()
        if not state:
            state = RiskState(user_id=user_id, session_id=session_id)
            db.session.add(state)
            db.session.commit()
        return state

    @staticmethod
    def evaluate(
        session_id: str,
        is_new_device: bool = False,
        fp_hash: Optional[str] = None,
    ) -> RiskState:
        """Evaluate risk signals and update state."""
        from services.session_service import SessionService

        session = SessionService.get(session_id)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")

        state = RiskService.get_or_create(session.user_id, session_id)

        if is_new_device:
            state.score += 2
            logger.debug("Risk +2: new device for session %s", session_id[:8])

        # Burst detection
        cutoff = utcnow() - timedelta(seconds=Config.RISK_BURST_WINDOW_SECONDS)
        recent_count = (
            Event.query.filter(
                Event.session_id == session_id,
                Event.timestamp >= cutoff,
            ).count()
        )
        if recent_count >= Config.RISK_BURST_MAX_EVENTS:
            state.score += 3
            logger.warning("Risk +3: burst activity on session %s", session_id[:8])

        # Fingerprint reuse anomaly
        if fp_hash and FingerprintService.is_reused_abnormally(fp_hash):
            state.score += 4
            logger.warning("Risk +4: fingerprint reuse anomaly %s", fp_hash[:8])

        state.update_status(Config.RISK_THROTTLE_THRESHOLD, Config.RISK_BLOCK_THRESHOLD)
        db.session.commit()
        return state

    @staticmethod
    def get_status(session_id: str) -> str:
        state = RiskState.query.filter_by(session_id=session_id).first()
        return state.status if state else RISK_OK

    @staticmethod
    def reset(session_id: str) -> None:
        state = RiskState.query.filter_by(session_id=session_id).first()
        if state:
            state.score = 0
            state.status = RISK_OK
            db.session.commit()
