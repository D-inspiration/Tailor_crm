"""
Provider abstraction layer.
Hide webhook complexity behind a uniform interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class EmailProvider(ABC):
    """
    Abstract base for all inbound email providers.
    Polymorphic: same interface, different implementations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier string."""
        ...

    @abstractmethod
    def receive(self, payload: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """
        Receive and normalize a webhook payload.
        Returns a standardized dict for Message creation.
        """
        ...

    @abstractmethod
    def verify(self, payload: Dict[str, Any], signature: str) -> bool:
        """Validate webhook authenticity."""
        ...

    def normalize_attachments(self, raw_attachments: list) -> list:
        """Optional hook to standardize attachment metadata."""
        return raw_attachments
