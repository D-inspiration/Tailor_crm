"""
Unit tests: SubscriptionService lifecycle.
"""

import pytest
from comm_platform.services.subscription_service import SubscriptionService
from comm_platform.core.constants import SubscriberStatus


class TestSubscriptionService:
    def test_register_creates_subscriber(self, db_session):
        svc = SubscriptionService()
        sub = svc.register("user@example.com", source="landing_page", tags=["beta"])
        assert sub.email == "user@example.com"
        assert sub.status == SubscriberStatus.PENDING.value
        assert "beta" in sub.tags

    def test_idempotent_registration(self, db_session):
        svc = SubscriptionService()
        first = svc.register("dup@example.com")
        second = svc.register("dup@example.com")
        assert first.id == second.id

    def test_confirm_changes_status(self, db_session):
        svc = SubscriptionService()
        svc.register("confirm@example.com")
        confirmed = svc.confirm("confirm@example.com")
        assert confirmed.status == SubscriberStatus.ACTIVE.value

    def test_unsubscribe(self, db_session):
        svc = SubscriptionService()
        svc.register("leave@example.com")
        svc.confirm("leave@example.com")
        unsub = svc.unsubscribe("leave@example.com")
        assert unsub.status == SubscriberStatus.UNSUBSCRIBED.value

    def test_tag_segmentation(self, db_session):
        svc = SubscriptionService()
        svc.register("tagged@example.com", tags=["newsletter"])
        svc.register("other@example.com", tags=["newsletter"])
        audience = svc.audience(tag="newsletter")
        assert len(audience) == 2
