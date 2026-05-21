"""Input validation helpers."""
import re
from typing import List, Optional

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def is_valid_email(email: str) -> bool:
    """Basic email format validation."""
    return bool(_EMAIL_RE.match(email))


def require_fields(data: dict, fields: List[str]) -> Optional[str]:
    """Return the first missing field name, or None if all present."""
    for f in fields:
        if f not in data or data[f] in (None, ""):
            return f
    return None
