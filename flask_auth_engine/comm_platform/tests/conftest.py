"""
Pytest configuration for comm_platform.
Uses an isolated in-memory SQLite database — no touching of your existing sbeae.db.
"""

import pytest
from flask import Flask
import os

# We need to mock the utils.extensions.db that your app uses
from unittest.mock import MagicMock


@pytest.fixture(scope="session")
def app():
    """Create a minimal Flask app with comm_platform mounted."""
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["COMM_RESEND_WEBHOOK_SECRET"] = os.getenv("RESEND_WEBHOOK_SECRET", "test-secret") 

    # Mock your existing db extension
    import utils.extensions
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, scoped_session
    from sqlalchemy.ext.declarative import declarative_base

    engine = create_engine("sqlite:///:memory:")
    db_session = scoped_session(sessionmaker(bind=engine))
    Base = declarative_base()
    Base.query = db_session.query_property()

    # Patch the db object your models import
    original_db = utils.extensions.db
    utils.extensions.db = MagicMock()
    utils.extensions.db.session = db_session
    utils.extensions.db.Model = Base
    utils.extensions.db.Column = lambda *a, **k: None  # Will be replaced by real SA

    # Import and init platform
    from comm_platform import init_comm_platform
    init_comm_platform(flask_app)

    # Create tables
    Base.metadata.create_all(bind=engine)

    yield flask_app

    # Restore
    utils.extensions.db = original_db
    db_session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Provide a transactional scope around a test."""
    import utils.extensions
    connection = utils.extensions.db.session.bind.connect()
    transaction = connection.begin()

    yield utils.extensions.db.session

    transaction.rollback()
    connection.close()
