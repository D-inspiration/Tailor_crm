"""Plan limit enforcement guard."""
from services.subscription_service import SubscriptionService
from utils.logger import get_logger

logger = get_logger("SubscriptionGuard")


class SubscriptionGuard:
    """Returns allow/deny based on current usage vs plan caps."""

    @staticmethod
    def validate(user_id: int, resource: str) -> tuple[bool, str]:
        sub = SubscriptionService.get_or_create(user_id)
        if not sub:
            return False, "no_subscription"
        if not sub.is_active():
            return False, "subscription_expired"
        if sub.limit_exceeded(resource):
            logger.warning(
                "Limit exceeded for user %s resource=%s plan=%s",
                user_id, resource, sub.plan,
            )
            return False, f"limit_exceeded:{resource}"
        return True, "ok"

    @staticmethod
    def validate_write_access(user_id: int, resource: str) -> tuple[bool, str]:
        sub = SubscriptionService.get_or_create(user_id)
        
        if sub.status == SUB_LOCKED:
            return False, "account_locked_renew_required"
        
        if sub.status == SUB_GRACE:
            # Allow reads, block writes
            if resource in ("customers", "orders", "create", "update", "delete"):
                return False, "grace_period_write_blocked"
            return True, "ok"
        
        # Normal limit check
        return SubscriptionGuard.validate(user_id, resource)

    @staticmethod
    def validate_downgrade_state(user_id: int) -> dict:
        sub = SubscriptionService.get_or_create(user_id)
        
        if sub.plan == "free" and sub.was_previously_paid:
            # Count current assets
            stats = {
                "customers": CustomerService.count(user_id),
                "orders": OrderService.count(user_id),
                "sessions": SessionService.active_count(user_id),
            }
            
            overages = {}
            for resource, count in stats.items():
                limit = sub.limits.get(resource, 0)
                if limit != -1 and count > limit:
                    overages[resource] = {"current": count, "limit": limit}
            
            if overages:
                return {
                    "status": "locked",
                    "reason": "downgrade_quota_exceeded",
                    "overages": overages,
                    "action_required": "upgrade_or_archive",
                }
        
        return {"status": "ok"}

