"""Unit tests for AuthService."""
import pytest
from services.auth_service import AuthService
from utils.extensions import db


class TestAuthService:
    def test_register_creates_user(self, app):
        with app.app_context():
            user = AuthService.register("test@example.com", "+123", "secret")
            assert user.id is not None
            assert user.email == "test@example.com"

    def test_register_duplicate_email_raises(self, app):
        with app.app_context():
            AuthService.register("dup@example.com", "+123", "secret")
            with pytest.raises(ValueError, match="already registered"):
                AuthService.register("dup@example.com", "+456", "other")

    def test_authenticate_success(self, app):
        with app.app_context():
            AuthService.register("auth@example.com", "+123", "secret")
            ok, user = AuthService.authenticate("auth@example.com", "secret")
            assert ok is True
            assert user is not None

    def test_authenticate_wrong_password(self, app):
        with app.app_context():
            AuthService.register("wrong@example.com", "+123", "secret")
            ok, user = AuthService.authenticate("wrong@example.com", "bad")
            assert ok is False
            assert user is None

    def test_authenticate_inactive_user(self, app):
        with app.app_context():
            user = AuthService.register("inactive@example.com", "+123", "secret")
            user.is_active = False
            db.session.commit()
            ok, _ = AuthService.authenticate("inactive@example.com", "secret")
            assert ok is False
