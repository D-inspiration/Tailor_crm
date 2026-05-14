import requests
from django.conf import settings

FLASK_AUTH_URL = getattr(settings, 'FLASK_AUTH_URL', 'http://127.0.0.1:5050')
FLASK_SERVICE_SECRET = getattr(settings, 'FLASK_SERVICE_KEY', 'django-flask-shared-secret')


class SubscriptionClient:
    @staticmethod
    def _headers():
        return {
            "Content-Type": "application/json",
            "X-Service-Secret": FLASK_SERVICE_SECRET
        }

    @staticmethod
    def check_limit(user_id, resource):
        """
        Check if user can use resource.
        Resources: customers, orders_per_month, storage_mb, staff_accounts, api_calls, events_per_day
        """
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/event/process",
                json={
                    "event_type": "action",
                    "session_id": "django-limit-check",
                    "user_id": user_id,
                    "payload": {"action_type": "limit_check", "resource": resource}
                },
                timeout=3,
                headers=SubscriptionClient._headers()
            )
            data = res.json()
            if data.get("status") == "allow":
                return True, "ok"
            return False, data.get("reason", "denied")
        except Exception:
            # Fail-open for offline (allow but warn)
            return True, "offline_allowed"

    @staticmethod
    def get_usage(user_id):
        """Get current subscription status and usage."""
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/session/list",
                json={"user_id": user_id},
                timeout=3,
                headers=SubscriptionClient._headers()
            )
            # This returns sessions, not subscription. Need proper endpoint.
            # For now, return empty and we'll add a /subscription/status endpoint later
            return {}
        except Exception:
            return {}

    @staticmethod
    def get_plan(user_id):
        """Get user's current plan name."""
        # Will need Flask endpoint. For now, infer from limits.
        return "free"  # Placeholder

            