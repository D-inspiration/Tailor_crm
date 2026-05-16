"""
services/subscription_client.py
Django-side HTTP client that talks to the Flask auth engine's subscription endpoints.
"""

import requests
from dataclasses import dataclass, field
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

FLASK_AUTH_URL = "http://127.0.0.1:5050"

_HEADERS = {
    "Content-Type": "application/json",
    "X-Service-Secret": "django-flask-shared-secret",
}


# =========================================================
# DATA MODEL
# =========================================================

@dataclass
class SubscriptionData:
    """
    Safe normalized structure:
    - guarantees dicts for usage/limits
    - prevents template key errors
    """

    plan: str = "free"
    status: str = "active"
    limits: Dict[str, Any] = field(default_factory=dict)
    usage: Dict[str, Any] = field(default_factory=dict)
    user_id: int = 0

    # -------------------------------
    # Safe API parsing
    # -------------------------------
    @classmethod
    def from_api_response(cls, data: dict) -> 'SubscriptionData':
        """
        Supports both:
        A) {"subscription": {...}}
        B) direct flat response {"usage": {...}, "limits": {...}}
        """
    
        # Case 1: nested subscription object
        if isinstance(data.get("subscription"), dict):
            sub = data["subscription"]
        else:
            # Case 2: flat Flask response
            sub = data
    
        return cls(
            plan=sub.get("plan", "free"),
            status=sub.get("status", "active"),
            limits=sub.get("limits", {}),
            usage=sub.get("usage", {}),
            user_id=data.get("user_id", sub.get("user_id", 0)),
        )

    # =========================================================
    # CORE SAFE ACCESSORS
    # =========================================================

    def _u(self, key: str) -> int:
        try:
            return int(self.usage.get(key, 0) or 0)
        except Exception:
            return 0

    def _l(self, key: str, default: int = 0) -> int:
        try:
            return int(self.limits.get(key, default) or default)
        except Exception:
            return default

    # =========================================================
    # USAGE METRICS
    # =========================================================

    @property
    def customer_usage(self) -> int:
        return self._u("customers")

    @property
    def customer_limit(self) -> int:
        return self._l("customers", 20)

    @property
    def order_usage(self) -> int:
        return self._u("orders")

    @property
    def order_limit(self) -> int:
        return self._l("orders_per_month", 10)

    @property
    def session_usage(self) -> int:
        return self._u("sessions")

    @property
    def session_limit(self) -> int:
        return self._l("sessions", 5)

    @property
    def api_usage(self) -> int:
        return self._u("api_calls")

    @property
    def api_limit(self) -> int:
        return self._l("api_calls", 100)

    @property
    def storage_usage(self) -> int:
        return self._u("storage_mb")

    @property
    def storage_limit(self) -> int:
        return self._l("storage_mb", 50)

    @property
    def staff_usage(self) -> int:
        return self._u("staff_accounts")

    @property
    def staff_limit(self) -> int:
        return self._l("staff_accounts", 1)

    @property
    def events_usage(self) -> int:
        return self._u("events_per_day")

    @property
    def events_limit(self) -> int:
        return self._l("events_per_day", 500)

    # =========================================================
    # UI HELPERS
    # =========================================================

    @property
    def customer_percent(self) -> int:
        limit = self.customer_limit
        if limit <= 0:
            return 0
        return min(int((self.customer_usage / limit) * 100), 100)

    @property
    def is_near_limit(self) -> bool:
        return self.customer_usage >= (self.customer_limit - 3)

    @property
    def is_at_limit(self) -> bool:
        return self.customer_usage >= self.customer_limit

    @property
    def customers_remaining(self) -> int:
        return max(0, self.customer_limit - self.customer_usage)


# =========================================================
# CLIENT
# =========================================================

class SubscriptionClient:

    # -------------------------------
    # INTERNAL HEADERS
    # -------------------------------
    @staticmethod
    def _headers():
        return _HEADERS

    # -------------------------------
    # GET USAGE
    # -------------------------------
    @staticmethod
    def get_usage(user_id: int) -> SubscriptionData:
        """Fetch current subscription + usage from Flask."""
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/session/subscription/status",
                headers=_HEADERS,
                json={"user_id": user_id},
                timeout=5,
            )
            res.raise_for_status()
            data = res.json()
    
            # DEBUG (safe inside try)
            print("\n[SUB_CLIENT_RAW_RESPONSE]")
            print(data)
            print("[SUB_CLIENT_PARSED_USAGE]", data.get("usage"))
    
            return SubscriptionData.from_api_response(data)
    
        except Exception as e:
            logger.warning(
                "SubscriptionClient.get_usage failed for user %s: %s",
                user_id, e
            )
            return SubscriptionData(user_id=user_id)

    # -------------------------------
    # CHECK LIMIT
    # -------------------------------
    @staticmethod
    def check_limit(user_id: int, resource: str) -> tuple[bool, str]:
        sub = SubscriptionClient.get_usage(user_id)

        usage = sub.usage.get(resource, 0) or 0
        limit = sub.limits.get(resource, 10) or 10

        try:
            usage = int(usage)
            limit = int(limit)
        except Exception:
            usage, limit = 0, 10

        if limit != -1 and usage >= limit:
            return False, f"{resource}_limit_reached"

        return True, "ok"

    # -------------------------------
    # INCREMENT USAGE
    # -------------------------------
    @staticmethod
    def increment_usage(user_id: int, resource: str, session_id: str = None) -> dict:
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/event/subscription/increment",
                headers=_HEADERS,
                json={"user_id": user_id, "resource": resource},
                timeout=5,
            )
            res.raise_for_status()
            return res.json()

        except Exception as e:
            logger.warning(
                "[SubscriptionClient] increment failed user=%s resource=%s err=%s",
                user_id, resource, e
            )
            return {"status": "error", "detail": str(e)}

    # -------------------------------
    # HARD SET (CRITICAL SYNC FIX)
    # -------------------------------
    @staticmethod
    def set_usage(user_id: int, resource: str, value: int) -> dict:
        try:
            logger.debug(
                "[SubscriptionClient] set_usage -> user=%s resource=%s value=%s",
                user_id, resource, value
            )

            res = requests.post(
                f"{FLASK_AUTH_URL}/event/subscription/set_usage",
                headers=_HEADERS,
                json={
                    "user_id": user_id,
                    "resource": resource,
                    "value": int(value),
                },
                timeout=5,
            )

            res.raise_for_status()
            data = res.json()

            logger.debug("[SubscriptionClient] set_usage response: %s", data)

            return data

        except Exception as e:
            logger.warning(
                "[SubscriptionClient] set_usage failed user=%s resource=%s value=%s err=%s",
                user_id, resource, value, e
            )
            return {"status": "error", "detail": str(e)}

    # -------------------------------
    # UPGRADE PLAN
    # -------------------------------
    @staticmethod
    def upgrade_plan(user_id: int, plan: str) -> bool:
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/session/subscription/upgrade",
                json={"user_id": user_id, "plan": plan},
                headers=_HEADERS,
                timeout=5,
            )

            if res.status_code == 200:
                logger.info("[SubscriptionClient] upgraded user=%s plan=%s", user_id, plan)
                return True

            logger.warning(
                "[SubscriptionClient] upgrade failed status=%s body=%s",
                res.status_code,
                res.text,
            )
            return False

        except Exception as e:
            logger.error("[SubscriptionClient] upgrade error user=%s err=%s", user_id, e)
            return False
    

            