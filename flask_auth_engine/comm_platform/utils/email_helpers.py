"""
Email utility helpers — preview extraction, link parsing, sanitization.
"""

import re
from typing import List


def extract_preview(text: str, length: int = 100) -> str:
    """Generate plain-text preview from body."""
    if not text:
        return ""
    # Strip extra whitespace
    cleaned = " ".join(text.split())
    if len(cleaned) <= length:
        return cleaned
    return cleaned[:length] + "..."


def extract_links(text: str) -> List[str]:
    """Find all HTTP(S) URLs in text or HTML."""
    return re.findall(r"https?://[^\s<<>'\"]+", text)


def sanitize_sender(email: str) -> str:
    """Basic sender email normalization."""
    return email.strip().lower() if email else ""


def parse_email_address(raw: str) -> tuple:
    """
    Parse 'Name <email@example.com>' into (name, email).
    """
    match = re.match(r'^(.*?)\s*<([^>]+)>\s*$', raw)
    if match:
        return match.group(1).strip('"').strip(), match.group(2).strip()
    return "", raw.strip()
