"""utils/hash.py"""
import hashlib
import hmac
import secrets
import string


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hmac_sha256(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def generate_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_session_id() -> str:
    return secrets.token_urlsafe(32)


"""utils/time.py"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(dt: datetime) -> bool:
    return utcnow() > dt


def seconds_until(dt: datetime) -> float:
    delta = dt - utcnow()
    return max(0.0, delta.total_seconds())
