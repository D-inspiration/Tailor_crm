"""Billing logic — plan periods, renewal math, proration."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from utils.logger import get_logger

logger = get_logger("BillingService")

# ── Plan Periods ─────────────────────────────────────────────────────────────
PLAN_PERIODS = {
    "monthly":   {"months": 1,  "label": "1 month"},
    "quarterly": {"months": 3,  "label": "3 months"},
    "biannual":  {"months": 6,  "label": "6 months"},
    "yearly":    {"months": 12, "label": "12 months"},
}


def get_period_months(period_key: str) -> int:
    """Return number of months for a billing period."""
    return PLAN_PERIODS.get(period_key, PLAN_PERIODS["monthly"])["months"]


def calculate_new_expiry(
    current_expires_at: Optional[datetime],
    period_months: int
) -> datetime:
    """
    Extend from current expiry if active, else start from now.
    Handles month/year rollover and day overflow correctly.
    """
    now = datetime.now(timezone.utc)

    if current_expires_at and current_expires_at > now:
        base = current_expires_at
        logger.debug("Extending from current expiry: %s", base.isoformat())
    else:
        base = now
        logger.debug("Starting fresh from: %s", base.isoformat())

    # Add months with rollover handling
    new_month = base.month + period_months
    new_year = base.year + (new_month - 1) // 12
    new_month = ((new_month - 1) % 12) + 1

    # Clamp day to max of target month (e.g. Jan 31 + 1 mo → Feb 28)
    max_day = (datetime(new_year, new_month, 1, tzinfo=timezone.utc) - timedelta(days=1)).day
    new_day = min(base.day, max_day)

    return datetime(
        new_year, new_month, new_day,
        base.hour, base.minute, base.second,
        tzinfo=timezone.utc,
    )
