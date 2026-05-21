"""Pytest fixtures and configuration."""
import pytest
from app import create_app
from config import TestConfig
from utils.extensions import db


@pytest.fixture
def app():
    """Create application for testing."""
    _app = create_app(TestConfig)
    with _app.app_context():
        db.create_all()
        yield _app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def auth_headers():
    """Valid service auth headers."""
    from config import TestConfig
    return {"X-Service-Secret": TestConfig.DJANGO_SHARED_SECRET}
