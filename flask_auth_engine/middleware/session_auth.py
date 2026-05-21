"""Session validation middleware."""
from functools import wraps
from flask import request, jsonify, g
from engine.session_guard import SessionGuard
from utils.logger import get_logger

logger = get_logger("SessionMiddleware")


def require_valid_session(fn):
    """Decorator: validates session and attaches to g.session."""
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

        from services.session_service import SessionService
        g.session = SessionService.get(session_id)
        return fn(*args, **kwargs)
    return wrapper
