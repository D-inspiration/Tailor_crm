class ActionEvent(BaseEvent):
    def process(self) -> Dict[str, Any]:
        from services.services import RiskService, EventService, SubscriptionService
        session = __import__("store").sessions.get(self.session_id)
        fp_hash = session.device_fingerprint if session else None

        risk = RiskService.evaluate(
            session_id=self.session_id,
            is_new_device=self.payload.get("is_new_device", False),
            fp_hash=fp_hash,
        )
        event = EventService.record(
            session_id=self.session_id,
            user_id=self.user_id,
            event_type="action",
            payload=self.payload,
        )
        
        # Base resources
        SubscriptionService.increment(self.user_id, "events_per_day")
        SubscriptionService.increment(self.user_id, "api_calls")
        
        # CRM-specific resources based on action_type
        action_type = self.payload.get("action_type", "")
        if action_type == "customer_created":
            SubscriptionService.increment(self.user_id, "customers")
        elif action_type == "order_created":
            SubscriptionService.increment(self.user_id, "orders_per_month")
        elif action_type == "gallery_image_added":
            # Approximate storage tracking (simplified)
            image_size = self.payload.get("image_size_mb", 0.5)
            SubscriptionService.increment(self.user_id, "storage_mb", amount=image_size)
        
        logger.debug("ActionEvent processed, risk=%s", risk.status)
        return {"event_id": event.id, "risk_status": risk.status}
        