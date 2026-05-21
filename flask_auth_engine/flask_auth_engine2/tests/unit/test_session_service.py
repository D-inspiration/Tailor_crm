"""Unit tests for SessionService."""
from services.session_service import SessionService
from services.auth_service import AuthService
from services.subscription_service import SubscriptionService
from models.session import SESSION_ACTIVE, SESSION_REVOKED


class TestSessionService:
    def test_create_session(self, app):
        with app.app_context():
            user = AuthService.register("s@example.com", "+1", "pw")
            SubscriptionService.get_or_create(user.id)
            session = SessionService.create(user.id, "fp123")
            assert session.id is not None
            assert session.status == SESSION_ACTIVE
            assert session.user_id == user.id

    def test_validate_active_session(self, app):
        with app.app_context():
            user = AuthService.register("v@example.com", "+1", "pw")
            SubscriptionService.get_or_create(user.id)
            session = SessionService.create(user.id, "fp123")
            assert SessionService.validate(session.id) is True

    def test_revoke_session(self, app):
        with app.app_context():
            user = AuthService.register("r@example.com", "+1", "pw")
            SubscriptionService.get_or_create(user.id)
            session = SessionService.create(user.id, "fp123")
            SessionService.revoke(session.id)
            assert session.status == SESSION_REVOKED
            assert SessionService.validate(session.id) is False

    def test_revoke_all_for_user(self, app):
        with app.app_context():
            user = AuthService.register("ra@example.com", "+1", "pw")
            SubscriptionService.get_or_create(user.id)
            s1 = SessionService.create(user.id, "fp1")
            s2 = SessionService.create(user.id, "fp2")
            count = SessionService.revoke_all_for_user(user.id)
            assert count == 2
            assert s1.status == SESSION_REVOKED
            assert s2.status == SESSION_REVOKED
