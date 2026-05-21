"""Unit tests for SubscriptionGuard."""
from engine.subscription_guard import SubscriptionGuard
from services.subscription_service import SubscriptionService
from services.auth_service import AuthService


class TestSubscriptionGuard:
    def test_allow_within_limit(self, app):
        with app.app_context():
            user = AuthService.register("sub@example.com", "+1", "pw")
            SubscriptionService.get_or_create(user.id)
            ok, reason = SubscriptionGuard.validate(user.id, "api_calls")
            assert ok is True
            assert reason == "ok"

    def test_deny_when_limit_exceeded(self, app):
        with app.app_context():
            user = AuthService.register("sub2@example.com", "+1", "pw")
            SubscriptionService.get_or_create(user.id)
            sub = SubscriptionService.get_or_create(user.id)
            sub.usage["api_calls"] = 100
            from utils.extensions import db
            db.session.commit()
            ok, reason = SubscriptionGuard.validate(user.id, "api_calls")
            assert ok is False
            assert "limit_exceeded" in reason
