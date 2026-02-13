"""User repository implementation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import User
from src.domain.enums import UserRole
from src.domain.repositories import IUserRepository
from src.infrastructure.database.models import UserModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemyUserRepository(SQLAlchemyRepository[UserModel, User], IUserRepository):
    """SQLAlchemy implementation of User repository."""

    model_class = UserModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        stmt = select(UserModel).where(UserModel.email == email.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_role(
        self,
        role: UserRole,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """Get users by role."""
        stmt = (
            select(UserModel)
            .where(UserModel.role == role)
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_active_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all active users."""
        stmt = (
            select(UserModel)
            .where(UserModel.is_active.is_(True))
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def email_exists(self, email: str, exclude_id: UUID | None = None) -> bool:
        """Check if email is already registered."""
        stmt = select(func.count()).where(UserModel.email == email.lower())
        if exclude_id:
            stmt = stmt.where(UserModel.id != exclude_id)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count is not None and count > 0

    def _to_entity(self, model: UserModel) -> User:
        """Convert ORM model to domain entity."""
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            role=model.role,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: User) -> UserModel:
        """Convert domain entity to ORM model."""
        return UserModel(
            id=entity.id,
            email=entity.email.lower(),
            hashed_password=entity.hashed_password,
            role=entity.role,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
