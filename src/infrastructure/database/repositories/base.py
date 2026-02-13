"""Base SQLAlchemy repository implementation."""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)
EntityT = TypeVar("EntityT")


class SQLAlchemyRepository(Generic[ModelT, EntityT]):
    """Base SQLAlchemy repository with common CRUD operations."""

    model_class: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: UUID) -> EntityT | None:
        """Get entity by ID."""
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[EntityT]:
        """Get all entities with pagination."""
        stmt = (
            select(self.model_class)
            .order_by(self.model_class.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save(self, entity: EntityT) -> EntityT:
        """Save entity (create or update)."""
        model = self._to_model(entity)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return self._to_entity(merged)

    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID."""
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists."""
        stmt = select(func.count()).where(self.model_class.id == entity_id)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count is not None and count > 0

    async def count(self) -> int:
        """Get total count of entities."""
        stmt = select(func.count()).select_from(self.model_class)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    def _to_entity(self, model: ModelT) -> EntityT:
        """Convert ORM model to domain entity. Override in subclass."""
        raise NotImplementedError

    def _to_model(self, entity: EntityT) -> ModelT:
        """Convert domain entity to ORM model. Override in subclass."""
        raise NotImplementedError
