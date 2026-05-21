"""
Unit tests: Provider abstraction and polymorphism.
"""

import pytest
from comm_platform.providers.resend_provider import ResendProvider
from comm_platform.providers.ses_provider import SESProvider
from comm_platform.providers.base import EmailProvider


class TestProviderPolymorphism:
    def test_resend_normalizes_payload(self):
        provider = ResendProvider()
        raw = {
            "from": "sender@test.com",
            "to": ["recipient@test.com"],
            "subject": "Hi",
            "text": "Body",
            "html": "<p>Body</p>",
        }
        result = provider.receive(raw, "")
        assert result["sender"] == "sender@test.com"
        assert result["recipient"] == "recipient@test.com"
        assert result["provider"] == "resend"

    def test_provider_interface_contract(self):
        """All providers must implement the abstract interface."""
        for cls in [ResendProvider, SESProvider]:
            assert issubclass(cls, EmailProvider)
            inst = cls()
            assert hasattr(inst, "receive")
            assert hasattr(inst, "verify")
            assert hasattr(inst, "name")
            assert isinstance(inst.name, str)
