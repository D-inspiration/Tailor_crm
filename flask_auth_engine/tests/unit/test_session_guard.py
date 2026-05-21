"""Unit tests for SessionGuard."""
from engine.session_guard import SessionGuard
from services.session_service import SessionService
from services.auth_service import AuthService
from services.subscription_service import SubscriptionService


class TestSessionGuard:
    def test_validate_missing_session(self, app):
        with app.app_context():
            ok, reason = SessionGuard.validate("nonexistent")
            assert ok is False
            assert reason == "session_not_found"

    def test_validate_valid_session(self, app):
        with app.app_context():
            user = AuthService.register("sg@example.com", "+1", "pw")
            SubscriptionService.get_or_create(user.id)
            session = SessionService.create(user.id, "fp1")
            ok, reason = SessionGuard.validate(session.id)
            assert ok is True
            assert reason == "ok"

    def test_validate_user_mismatch(self, app):
        with app.app_context():
            u1 = AuthService.register("u1@example.com", "+1", "pw")
            u2 = AuthService.register("u2@example.com", "+2", "pw")
            SubscriptionService.get_or_create(u1.id)
            SubscriptionService.get_or_create(u2.id)
            session = SessionService.create(u1.id, "fp1")
            ok, reason = SessionGuard.validate(session.id, user_id=u2.id)
            assert ok is False
            assert reason == "session_user_mismatch"

    def test_validate_revoked_session(self, app):
        with app.app_context():
            user = AuthService.register("rev@example.com", "+1", "pw")
            SubscriptionService.get_or_create(user.id)
            session = SessionService.create(user.id, "fp1")
            SessionService.revoke(session.id)
            ok, reason = SessionGuard.validate(session.id)
            assert ok is False
            assert "revoked" in reason
