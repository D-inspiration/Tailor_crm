"""
Attachment metadata — files stored externally (S3/MinIO), metadata here.
"""

from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import BaseModel


class Attachment(BaseModel):
    """Represents a file attached to a message."""

    __tablename__ = "comm_attachments"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("comm_messages.id"), nullable=False)
    message: Mapped["Message"] = relationship("Message", back_populates="attachments")
