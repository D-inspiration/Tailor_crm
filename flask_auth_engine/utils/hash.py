"""Cryptographic hash utilities."""
import hashlib
import hmac
import secrets
import string


def sha256(data: str) -> str:
    """Return hex digest of SHA-256."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hmac_sha256(key: str, message: str) -> str:
    """Return HMAC-SHA256 hex digest."""
    return hmac.new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def generate_session_id() -> str:
    """Generate a cryptographically secure session identifier."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(64))
