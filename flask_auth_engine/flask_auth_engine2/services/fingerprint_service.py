"""Device fingerprint service."""
from typing import Optional
from models.fingerprint import DeviceFingerprint
from utils.time import utcnow
from utils.logger import get_logger
from utils.extensions import db
from config import Config

logger = get_logger("FingerprintService")


class FingerprintService:
    """Manages device fingerprint trust scores."""

    @staticmethod
    def get_or_create(user_id: int, fp_hash: str) -> DeviceFingerprint:
        """Retrieve or create a fingerprint record for a user."""
        fp = (
            DeviceFingerprint.query.filter_by(
                fingerprint_hash=fp_hash, user_id=user_id
            ).first()
        )
        if fp:
            fp.last_seen_at = utcnow()
            db.session.commit()
            return fp

        # Check if hash exists for a DIFFERENT user
        other = DeviceFingerprint.query.filter_by(fingerprint_hash=fp_hash).first()
        if other:
            logger.warning(
                "Fingerprint %s already owned by user %s, new entry for user %s",
                fp_hash[:8], other.user_id, user_id,
            )

        new_fp = DeviceFingerprint(user_id=user_id, fingerprint_hash=fp_hash)
        db.session.add(new_fp)
        db.session.commit()
        return new_fp

    @staticmethod
    def degrade(fp_hash: str, amount: float = Config.FINGERPRINT_TRUST_DECAY) -> None:
        """Reduce trust for a fingerprint."""
        fp = DeviceFingerprint.query.filter_by(fingerprint_hash=fp_hash).first()
        if fp:
            fp.degrade_trust(amount)
            db.session.commit()

    @staticmethod
    def is_reused_abnormally(fp_hash: str) -> bool:
        """Check if fingerprint is shared by more than allowed users."""
        owners = (
            db.session.query(DeviceFingerprint.user_id)
            .filter_by(fingerprint_hash=fp_hash)
            .distinct()
            .count()
        )
        return owners > Config.FINGERPRINT_REUSE_MAX_USERS

    @staticmethod
    def get_trust(fp_hash: str) -> float:
        """Return trust score for a fingerprint (0.5 default if unknown)."""
        fp = DeviceFingerprint.query.filter_by(fingerprint_hash=fp_hash).first()
        return fp.trust_score if fp else 0.5
