"""utils/validators.py"""
import re
from typing import Any, Dict, List, Optional

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?[1-9]\d{6,14}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_RE.match(phone))


def require_fields(data: Dict[str, Any], fields: List[str]) -> Optional[str]:
    """Return first missing field name, or None if all present."""
    for field in fields:
        if field not in data or data[field] is None:
            return field
    return None


def sanitize_string(value: str, max_length: int = 255) -> str:
    return str(value).strip()[:max_length]
