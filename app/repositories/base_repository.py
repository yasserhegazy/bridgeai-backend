"""Base repository class with common database operations."""

from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository providing common CRUD operations."""

    def __init__(self, model: Type[T], db: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Get all entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj: T) -> T:
        """
        Create new entity.

        Args:
            obj: Entity to create

        Returns:
            Created entity
        """
        self.db.add(obj)
        self.db.flush()
        self.db.refresh(obj)
        return obj

    def update(self, obj: T) -> T:
        """
        Update entity.

        Args:
            obj: Entity to update

        Returns:
            Updated entity
        """
        self.db.flush()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        """
        Delete entity.

        Args:
            obj: Entity to delete
        """
        self.db.delete(obj)
        self.db.flush()

    def count(self) -> int:
        """
        Count all entities.

        Returns:
            Number of entities
        """
        return self.db.query(func.count(self.model.id)).scalar()

    def exists(self, **filters) -> bool:
        """
        Check if entity exists with given filters.

        Args:
            **filters: Filter conditions

        Returns:
            True if entity exists, False otherwise
        """
        query = self.db.query(self.model)
        for key, value in filters.items():
            query = query.filter(getattr(self.model, key) == value)
        return query.first() is not None
