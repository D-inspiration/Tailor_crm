"""
Repository pattern — abstracts SQLAlchemy for future database swaps.
All concrete repositories inherit from BaseRepository.
"""

from typing import TypeVar, Type, List, Optional, Generic
from sqlalchemy import desc
from utils.extensions import db  # Your existing SQLAlchemy instance

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Generic CRUD operations.
    Hides query complexity behind clean method names.
    """

    def __init__(self, model_class: Type[T]):
        self._model = model_class

    # ------------------------------------------------------------------
    # Create / Update
    # ------------------------------------------------------------------
    def create(self, **kwargs) -> T:
        instance = self._model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance

    def update(self, instance: T, **kwargs) -> T:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        db.session.commit()
        return instance

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get_by_id(self, id: int) -> Optional[T]:
        return db.session.get(self._model, id)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        return (
            db.session.query(self._model)
            .order_by(desc(self._model.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def count(self) -> int:
        return db.session.query(self._model).count()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete(self, instance: T) -> None:
        db.session.delete(instance)
        db.session.commit()
