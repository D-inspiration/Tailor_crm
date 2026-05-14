"""utils/logger.py"""
import logging
import sys
from functools import wraps


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


def log_event(logger: logging.Logger):
    """Decorator: log entry/exit of service methods."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            logger.debug("→ %s called", fn.__qualname__)
            result = fn(*args, **kwargs)
            logger.debug("← %s returned", fn.__qualname__)
            return result
        return wrapper
    return decorator
