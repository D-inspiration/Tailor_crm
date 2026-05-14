"""
middleware/auth_middleware.py
Validates the Django→Flask shared secret on every inbound request.
"""
from functools import wraps
from flask import request, jsonify, g
from config import Config
from utils.hash import constant_time_compare
from utils.logger import get_logger

logger = get_logger("AuthMiddleware")


def require_service_auth(fn):
    """
    Decorator: ensures caller is the Django service (shared secret header).
    Use on ALL controller endpoints.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        secret = request.headers.get("X-Service-Secret", "")
        if not constant_time_compare(secret, Config.DJANGO_SHARED_SECRET):
            logger.warning("Unauthorized request from %s", request.remote_addr)
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


"""
middleware/session_middleware.py
Validates session_id from request body / header and attaches to Flask g.
"""
from functools import wraps
from flask import request, jsonify, g
from engine.engine import SessionGuard
from utils.logger import get_logger

logger = get_logger("SessionMiddleware")


def require_valid_session(fn):
    """
    Decorator: validates session and user_id match; attaches session to g.session.
    JSON body must include: session_id, user_id.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id") or request.headers.get("X-Session-Id")
        user_id = data.get("user_id")

        if not session_id:
            return jsonify({"error": "session_id required"}), 400

        valid, reason = SessionGuard.validate(session_id, user_id)
        if not valid:
            logger.warning("Session validation failed: %s", reason)
            return jsonify({"status": "deny", "reason": reason}), 403

        import store
        g.session = store.sessions.get(session_id)
        return fn(*args, **kwargs)
    return wrapper


"""
middleware/rate_limit_middleware.py
Simple in-memory sliding-window rate limiter.
For production: replace with Redis + flask-limiter.
"""
import time
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify
from utils.logger import get_logger

logger = get_logger("RateLimitMiddleware")

_windows: dict = defaultdict(deque)   # key → deque of timestamps


def rate_limit(max_calls: int = 60, window_seconds: int = 60):
    """Decorator: limit requests per IP per window."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            key = f"{fn.__name__}:{ip}"
            now = time.monotonic()
            window = _windows[key]

            # Drop entries outside window
            while window and window[0] < now - window_seconds:
                window.popleft()

            if len(window) >= max_calls:
                logger.warning("Rate limit hit: %s", key)
                return jsonify({
                    "status": "throttle",
                    "reason": "rate_limit_exceeded"
                }), 429

            window.append(now)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
