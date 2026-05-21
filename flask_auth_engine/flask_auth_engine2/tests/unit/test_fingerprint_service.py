"""Unit tests for FingerprintService."""
from services.fingerprint_service import FingerprintService
from services.auth_service import AuthService


class TestFingerprintService:
    def test_get_or_create_new(self, app):
        with app.app_context():
            user = AuthService.register("fp@example.com", "+1", "pw")
            fp = FingerprintService.get_or_create(user.id, "hash123")
            assert fp.fingerprint_hash == "hash123"
            assert fp.user_id == user.id
            assert fp.trust_score == 1.0

    def test_degrade_trust(self, app):
        with app.app_context():
            user = AuthService.register("fp2@example.com", "+1", "pw")
            fp = FingerprintService.get_or_create(user.id, "hash456")
            FingerprintService.degrade("hash456", amount=0.3)
            assert fp.trust_score == 0.7

    def test_reuse_detection(self, app):
        with app.app_context():
            u1 = AuthService.register("fp3@example.com", "+1", "pw")
            u2 = AuthService.register("fp4@example.com", "+2", "pw")
            FingerprintService.get_or_create(u1.id, "shared_hash")
            FingerprintService.get_or_create(u2.id, "shared_hash")
            assert FingerprintService.is_reused_abnormally("shared_hash") is True
