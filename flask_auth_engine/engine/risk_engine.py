"""Pure risk evaluation — no side effects."""
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
    """Pure scoring function — isolated for testability."""

    WEIGHTS = {
        "is_new_device": 2,
        "is_burst": 3,
        "fingerprint_reused": 4,
        "low_trust_fingerprint": 2,
        "explicit_abuse": 5,
    }

    @staticmethod
    def score(signals: RiskSignals) -> int:
        total = 0
        for field, weight in RiskEngine.WEIGHTS.items():
            if getattr(signals, field, False):
                total += weight
                logger.debug("Risk +%d: %s", weight, field)
        return total
