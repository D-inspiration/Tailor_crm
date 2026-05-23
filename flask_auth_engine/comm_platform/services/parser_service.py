"""
Parser service — normalizes raw webhook payloads into domain objects.
Orchestrates provider selection and message creation.
"""

import json
from typing import Dict, Any, Type
from ..providers.base import EmailProvider
from ..providers.resend_provider import ResendProvider
from ..providers.ses_provider import SESProvider
from ..providers.postal_provider import PostalProvider
from ..core.constants import ProviderType


class ParserService:
    """
    Encapsulated message parsing.
    Selects provider dynamically based on header/payload hints.
    """

    _registry: Dict[str, Type[EmailProvider]] = {
        ProviderType.RESEND.value: ResendProvider,
        ProviderType.SES.value: SESProvider,
        ProviderType.POSTAL.value: PostalProvider,
    }

    def __init__(self):
        self._provider: EmailProvider | None = None

    def resolve(self, provider_name: str) -> EmailProvider:
        provider_class = self._registry.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        self._provider = provider_class()
        return self._provider

    def detect_provider(self, headers: Dict[str, str]) -> str:
        user_agent = headers.get("User-Agent", "").lower()
        if "resend" in user_agent:
            return ProviderType.RESEND.value
        if "amazon" in user_agent or "aws" in user_agent:
            return ProviderType.SES.value
        if "postal" in user_agent:
            return ProviderType.POSTAL.value
        return ProviderType.RESEND.value

    def parse(self, raw_body: bytes, signature: str, provider_name: str) -> Dict[str, Any]:
        provider = self.resolve(provider_name)

        # 🔐 verify FIRST using raw body
        if not provider.verify(raw_body, signature):
            raise PermissionError("Webhook signature verification failed")

        # 📦 decode AFTER verification
        payload = json.loads(raw_body.decode("utf-8"))

        # 🔄 normalize
        return provider.receive(payload, signature)
