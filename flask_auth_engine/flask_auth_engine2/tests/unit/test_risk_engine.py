"""Unit tests for RiskEngine."""
from engine.risk_engine import RiskEngine, RiskSignals


class TestRiskEngine:
    def test_no_signals_zero_score(self):
        signals = RiskSignals()
        assert RiskEngine.score(signals) == 0

    def test_new_device_score(self):
        signals = RiskSignals(is_new_device=True)
        assert RiskEngine.score(signals) == 2

    def test_burst_score(self):
        signals = RiskSignals(is_burst=True)
        assert RiskEngine.score(signals) == 3

    def test_fingerprint_reuse_score(self):
        signals = RiskSignals(fingerprint_reused=True)
        assert RiskEngine.score(signals) == 4

    def test_explicit_abuse_score(self):
        signals = RiskSignals(explicit_abuse=True)
        assert RiskEngine.score(signals) == 5

    def test_combined_signals(self):
        signals = RiskSignals(
            is_new_device=True,
            is_burst=True,
            fingerprint_reused=True,
        )
        assert RiskEngine.score(signals) == 9
