"""
Abstract base model providing common fields.
All platform models inherit from this — no duplicated fields.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from utils.extensions import db  # Import from YOUR existing app


class BaseModel(db.Model):
    """Abstract base with audit timestamps."""

    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def save(self) -> "BaseModel":
        """Persist to database."""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self) -> None:
        """Soft delete placeholder — override in concrete models if needed."""
        db.session.delete(self)
        db.session.commit()
