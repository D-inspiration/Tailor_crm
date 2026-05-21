"""Subscription plan management service."""
from typing import Optional
from models.subscription import Subscription, SUB_ACTIVE, DEFAULT_LIMITS
from utils.logger import get_logger
from utils.extensions import db

logger = get_logger("SubscriptionService")


class SubscriptionService:
    """Manages user subscriptions and plan limits."""

    @staticmethod
    def get_or_create(user_id: int, plan: str = "free") -> Subscription:
        sub = Subscription.query.filter_by(user_id=user_id).first()
        if not sub:
            sub = Subscription(user_id=user_id, plan=plan)
            db.session.add(sub)
            db.session.commit()
        return sub

    @staticmethod
    def is_limit_exceeded(user_id: int, resource: str) -> bool:
        sub = Subscription.query.filter_by(user_id=user_id).first()
        if not sub or not sub.is_active():
            return True
        return sub.limit_exceeded(resource)

    @staticmethod
    def increment(user_id: int, resource: str, amount: int = 1) -> None:
        sub = SubscriptionService.get_or_create(user_id)
        sub.increment_usage(resource, amount)
        db.session.commit()

    @staticmethod
    def update_plan(user_id: int, new_plan: str) -> Subscription:
        sub = SubscriptionService.get_or_create(user_id)
        sub.plan = new_plan
        sub.limits = DEFAULT_LIMITS.get(new_plan, DEFAULT_LIMITS["free"]).copy()
        db.session.commit()
        logger.info("User %s upgraded to plan: %s", user_id, new_plan)
        return sub
        
    @staticmethod
    def renew_or_extend(user_id: int, new_plan: str, payment_data: dict):
        sub = SubscriptionService.get_or_create(user_id)
        
        # If active and not expired yet: extend from current expiry
        if sub.is_active() and sub.expires_at and sub.expires_at > utcnow():
            new_expires = sub.expires_at + timedelta(days=30)  # or plan period
        else:
            # Expired or lapsed: start from now
            new_expires = utcnow() + timedelta(days=30)
        
        sub.expires_at = new_expires
        sub.status = SUB_ACTIVE
        sub.plan = new_plan
        db.session.commit()
        
        # Clear any "expiring soon" badges/flags
        BadgeService.clear(user_id, "expiring_soon")
        return sub
    
    @staticmethod
    def check_and_enforce_status(user_id: int):
        sub = SubscriptionService.get_or_create(user_id)
        
        if sub.status == SUB_ACTIVE and sub.expires_at and sub.expires_at < utcnow():
            # Just expired — enter grace
            sub.status = SUB_GRACE
            sub.grace_started_at = utcnow()
            db.session.commit()
            EmailService.send_grace_notice(user_id)
            return "grace"
        
        if sub.status == SUB_GRACE:
            grace_ended = sub.grace_started_at + timedelta(days=GRACE_PERIOD_DAYS)
            if utcnow() > grace_ended:
                # Grace over — hard lock
                sub.status = SUB_LOCKED
                db.session.commit()
                EmailService.send_lock_notice(user_id)
                return "locked"
        
        return sub.status
    