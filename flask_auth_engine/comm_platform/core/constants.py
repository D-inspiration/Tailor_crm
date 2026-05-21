"""
Domain constants and enums.
"""

from enum import Enum


class MessageStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
    SPAM = "spam"
    DELETED = "deleted"


class SubscriberStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"


class ProviderType(str, Enum):
    RESEND = "resend"
    SES = "ses"
    POSTAL = "postal"
    SMTP = "smtp"
