import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sbeae.db")

    # Session
    SESSION_TTL = timedelta(hours=int(os.getenv("SESSION_TTL_HOURS", 24)))
    SESSION_MAX_IDLE = timedelta(minutes=int(os.getenv("SESSION_MAX_IDLE_MINUTES", 30)))

    # Risk
    RISK_THROTTLE_THRESHOLD = int(os.getenv("RISK_THROTTLE_THRESHOLD", 6))
    RISK_BLOCK_THRESHOLD = int(os.getenv("RISK_BLOCK_THRESHOLD", 10))
    RISK_BURST_WINDOW_SECONDS = int(os.getenv("RISK_BURST_WINDOW_SECONDS", 10))
    RISK_BURST_MAX_EVENTS = int(os.getenv("RISK_BURST_MAX_EVENTS", 20))

    # Fingerprint
    FINGERPRINT_TRUST_DECAY = float(os.getenv("FINGERPRINT_TRUST_DECAY", 0.05))
    FINGERPRINT_REUSE_WINDOW_HOURS = int(os.getenv("FINGERPRINT_REUSE_WINDOW_HOURS", 1))
    FINGERPRINT_REUSE_MAX_USERS = int(os.getenv("FINGERPRINT_REUSE_MAX_USERS", 1))

    # Rate limiting
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "200 per minute")

    # Django integration
    DJANGO_SHARED_SECRET = os.getenv("DJANGO_SHARED_SECRET", "django-flask-shared-secret")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
