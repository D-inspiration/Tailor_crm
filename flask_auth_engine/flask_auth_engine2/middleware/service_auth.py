"""Service-to-service authentication middleware."""
from functools import wraps
from flask import request, jsonify
from config import Config
from utils.hash import constant_time_compare
from utils.logger import get_logger

logger = get_logger("AuthMiddleware")


def require_service_auth(fn):
    """Decorator: validates Django→Flask shared secret header."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        secret = request.headers.get("X-Service-Secret", "")
        if not constant_time_compare(secret, Config.DJANGO_SHARED_SECRET):
            logger.warning("Unauthorized request from %s", request.remote_addr)
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper
