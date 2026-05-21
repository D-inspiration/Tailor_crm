"""In-memory sliding-window rate limiter."""
import time
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify
from utils.logger import get_logger

logger = get_logger("RateLimitMiddleware")

_windows: dict = defaultdict(deque)


def rate_limit(max_calls: int = 60, window_seconds: int = 60):
    """Decorator: limit requests per IP per window."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            key = f"{fn.__name__}:{ip}"
            now = time.monotonic()
            window = _windows[key]

            while window and window[0] < now - window_seconds:
                window.popleft()

            if len(window) >= max_calls:
                logger.warning("Rate limit hit: %s", key)
                return jsonify({
                    "status": "throttle",
                    "reason": "rate_limit_exceeded",
                }), 429

            window.append(now)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
