"""
Integration tests: webhook ingestion → message creation.
"""

import pytest
from unittest.mock import patch


class TestResendWebhook:
    """End-to-end webhook acceptance tests."""

    def test_inbound_email_accepted(self, client):
        payload = {
            "from": "sender@example.com",
            "to": ["inbox@yourdomain.com"],
            "subject": "Test Subject",
            "text": "Hello world",
            "html": "<p>Hello world</p>",
        }
        headers = {
            "Authorization": "Bearer test-secret",
            "User-Agent": "Resend",
            "Content-Type": "application/json",
        }

        resp = client.post("/webhooks/resend/inbound", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "accepted"
        assert "message_id" in data

    def test_invalid_signature_rejected(self, client):
        payload = {"from": "bad@actor.com", "to": ["inbox@yourdomain.com"], "subject": "Bad"}
        headers = {
            "Authorization": "Bearer wrong-secret",
            "User-Agent": "Resend",
        }

        resp = client.post("/webhooks/resend/inbound", json=payload, headers=headers)
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "rejected"
