"""Base repository interface."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


class IRepository(Generic[T], ABC):
    """Base repository interface for all entities."""

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Get entity by ID.

        Args:
            entity_id: Entity UUID

        Returns:
            Entity if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Get all entities with pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        ...

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save entity (create or update).

        Args:
            entity: Entity to save

        Returns:
            Saved entity
        """
        ...

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID.

        Args:
            entity_id: Entity UUID

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists.

        Args:
            entity_id: Entity UUID

        Returns:
            True if exists, False otherwise
        """
        ...

    @abstractmethod
    async def count(self) -> int:
        """Get total count of entities.

        Returns:
            Total number of entities
        """
        ...
