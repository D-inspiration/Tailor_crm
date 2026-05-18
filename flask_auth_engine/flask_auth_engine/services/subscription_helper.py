# services/subscription_helper.py

from datetime import datetime
from store import SubscriptionStore
from models.models import Subscription   # adjust import path if needed


def ensure_subscription(user_id):

    print(
        f"[SUB DEBUG] "
        f"user_id={user_id} "
        f"type={type(user_id)}"
    )

    user_id = int(user_id)

    store = SubscriptionStore()

    sub = store.get(user_id)

    if not sub:
        default_limits = {
            "api_calls": 100,
            "customers": 20,
            "events_per_day": 500,
            "orders_per_month": 10,
            "sessions": 5,
            "staff_accounts": 1,
            "storage_mb": 50
        }

        usage = {
            "api_calls": 0,
            "customers": 0,
            "events_per_day": 0,
            "orders": 0,
            "orders_per_month": 0,
            "sessions": 0,
            "staff_accounts": 0,
            "storage_mb": 0
        }

        sub = Subscription(
            user_id=user_id,
            plan="free",
            status="active",
            limits=default_limits,
            usage=usage,
            created_at=datetime.utcnow(),
            expires_at=None
        )
        
        print(
            f"[SUB SAVE] "
            f"{sub.user_id=}"
        )

        store.save(sub)

        print(
            f"[SUB] Created free plan for user={user_id}"
        )

        sub = store.get(user_id)

    print(
        f"[ENGINE SUB] "
        f"user={user_id}, "
        f"plan={sub.plan}, "
        f"status={sub.status}"
    )

    return sub