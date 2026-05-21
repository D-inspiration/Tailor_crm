"""Application configuration."""
import os
from datetime import timedelta


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///sbeae.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"

    SESSION_TTL = timedelta(hours=int(os.getenv("SESSION_TTL_HOURS", 24)))
    SESSION_MAX_IDLE = timedelta(minutes=int(os.getenv("SESSION_MAX_IDLE_MINUTES", 30)))

    RISK_THROTTLE_THRESHOLD = int(os.getenv("RISK_THROTTLE_THRESHOLD", 6))
    RISK_BLOCK_THRESHOLD = int(os.getenv("RISK_BLOCK_THRESHOLD", 10))
    RISK_BURST_WINDOW_SECONDS = int(os.getenv("RISK_BURST_WINDOW_SECONDS", 10))
    RISK_BURST_MAX_EVENTS = int(os.getenv("RISK_BURST_MAX_EVENTS", 20))

    FINGERPRINT_TRUST_DECAY = float(os.getenv("FINGERPRINT_TRUST_DECAY", 0.05))
    FINGERPRINT_REUSE_WINDOW_HOURS = int(os.getenv("FINGERPRINT_REUSE_WINDOW_HOURS", 1))
    FINGERPRINT_REUSE_MAX_USERS = int(os.getenv("FINGERPRINT_REUSE_MAX_USERS", 1))

    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "200 per minute")
    DJANGO_SHARED_SECRET = os.getenv("DJANGO_SHARED_SECRET", "django-flask-shared-secret")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class TestConfig(Config):
    """Test configuration with in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_TTL = timedelta(hours=1)
    SESSION_MAX_IDLE = timedelta(minutes=5)
    RISK_BURST_WINDOW_SECONDS = 2
    RISK_BURST_MAX_EVENTS = 5
