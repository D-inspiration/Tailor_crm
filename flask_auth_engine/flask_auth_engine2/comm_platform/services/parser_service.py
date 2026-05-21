"""
Parser service — normalizes raw webhook payloads into domain objects.
Orchestrates provider selection and message creation.
"""

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

    # ------------------------------------------------------------------
    # Provider resolution
    # ------------------------------------------------------------------
    def resolve(self, provider_name: str) -> EmailProvider:
        """Factory method — returns polymorphic provider instance."""
        provider_class = self._registry.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        self._provider = provider_class()
        return self._provider

    def detect_provider(self, headers: Dict[str, str]) -> str:
        """Auto-detect provider from HTTP headers."""
        user_agent = headers.get("User-Agent", "").lower()
        if "resend" in user_agent:
            return ProviderType.RESEND.value
        if "amazon" in user_agent or "aws" in user_agent:
            return ProviderType.SES.value
        if "postal" in user_agent:
            return ProviderType.POSTAL.value
        return ProviderType.RESEND.value  # Default

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    def parse(self, payload: Dict[str, Any], signature: str, provider_name: str) -> Dict[str, Any]:
        """
        Full parse pipeline: verify → normalize.
        Returns dict ready for MessageRepository.create().
        """
        provider = self.resolve(provider_name)
        if not provider.verify(payload, signature):
            raise PermissionError("Webhook signature verification failed")
        return provider.receive(payload, signature)
