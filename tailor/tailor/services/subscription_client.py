import requests
from dataclasses import dataclass
from typing import Optional

FLASK_AUTH_URL = "http://127.0.0.1:5050"
FLASK_SERVICE_SECRET = "django-flask-shared-secret"


@dataclass
class SubscriptionData:
    plan: str
    status: str
    customer_usage: int
    customer_limit: int
    order_usage: int
    order_limit: int
    session_usage: int
    session_limit: int
    api_usage: int
    api_limit: int
    storage_usage: int
    storage_limit: int
    staff_usage: int
    staff_limit: int
    events_usage: int
    events_limit: int

    @classmethod
    def from_api_response(cls, data: dict) -> 'SubscriptionData':
        usage = data.get('usage', {}) if isinstance(data.get('usage'), dict) else {}
        limits = data.get('limits', {}) if isinstance(data.get('limits'), dict) else {}
        sub = data.get('subscription', {}) if isinstance(data.get('subscription'), dict) else {}
        
        return cls(
            plan=sub.get('plan', 'free'),
            status=sub.get('status', 'active'),
            customer_usage=usage.get('customers', 0),
            customer_limit=limits.get('customers', 20),
            order_usage=usage.get('orders', 0),
            order_limit=limits.get('orders_per_month', 10),
            session_usage=usage.get('sessions', 0),
            session_limit=limits.get('sessions', 5),
            api_usage=usage.get('api_calls', 0),
            api_limit=limits.get('api_calls', 100),
            storage_usage=usage.get('storage_mb', 0),
            storage_limit=limits.get('storage_mb', 50),
            staff_usage=usage.get('staff_accounts', 0),
            staff_limit=limits.get('staff_accounts', 1),
            events_usage=usage.get('events_per_day', 0),
            events_limit=limits.get('events_per_day', 500),
        )

    @property
    def customer_percent(self) -> int:
        if self.customer_limit == 0:
            return 0
        return min(int((self.customer_usage / self.customer_limit) * 100), 100)

    @property
    def is_near_limit(self) -> bool:
        return self.customer_usage >= self.customer_limit - 3

    @property
    def is_at_limit(self) -> bool:
        return self.customer_usage >= self.customer_limit


class SubscriptionClient:
    @staticmethod
    def _headers():
        return {
            'Content-Type': 'application/json',
            'X-Service-Secret': FLASK_SERVICE_SECRET
        }

    @staticmethod
    def get_usage(user_id) -> SubscriptionData:
        """Get current subscription status and usage from Flask."""
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/session/subscription/status",
                json={"user_id": user_id},
                timeout=5,
                headers=SubscriptionClient._headers()
            )
            if res.status_code == 200:
                data = res.json()
                print(f"[SubscriptionClient] Got usage: {data}")
                return SubscriptionData.from_api_response(data)
            print(f"[SubscriptionClient] Failed: {res.status_code} {res.text}")
            return SubscriptionData.from_api_response({})
        except Exception as e:
            print(f"[SubscriptionClient] Error: {e}")
            return SubscriptionData.from_api_response({})

    @staticmethod
    def check_limit(user_id, resource: str) -> tuple:
        """Check if user has hit limit for a resource."""
        sub = SubscriptionClient.get_usage(user_id)
        
        limit_map = {
            'customers': (sub.customer_usage, sub.customer_limit),
            'orders': (sub.order_usage, sub.order_limit),
            'sessions': (sub.session_usage, sub.session_limit),
        }
        
        usage, limit = limit_map.get(resource, (0, -1))
        
        if limit == -1:
            return True, "unlimited"
        if usage >= limit:
            return False, f"limit_exceeded:{resource}"
        return True, "ok"

    @staticmethod
    def increment_usage(user_id, resource: str) -> bool:
        print(f"[INCREMENT] user_id={user_id}, resource={resource}")
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/event/process",
                json={
                    "event_type": "action",
                    "user_id": user_id,
                    "payload": {"action_type": f"{resource}_created"}
                },
                timeout=5,
                headers={
                    'Content-Type': 'application/json',
                    'X-Service-Secret': FLASK_SERVICE_SECRET
                }
            )
            print(f"[INCREMENT] status={res.status_code}, body={res.text[:200]}")
            return res.status_code == 200
        except Exception as e:
            print(f"[INCREMENT] ERROR: {e}")
            return False


    @staticmethod
    def upgrade_plan(user_id, plan: str) -> bool:
        """Upgrade user subscription plan in Flask."""
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/session/subscription/upgrade",
                json={"user_id": user_id, "plan": plan},
                timeout=5,
                headers={
                    'Content-Type': 'application/json',
                    'X-Service-Secret': FLASK_SERVICE_SECRET
                }
            )
            if res.status_code == 200:
                print(f"[SubscriptionClient] Upgraded user {user_id} to {plan}")
                return True
            print(f"[SubscriptionClient] Upgrade failed: {res.status_code} {res.text}")
            return False
        except Exception as e:
            print(f"[SubscriptionClient] Upgrade error: {e}")
            return False
    

            