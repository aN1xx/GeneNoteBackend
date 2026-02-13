"""User repository interface."""

from abc import abstractmethod
from uuid import UUID

from src.domain.entities import User
from src.domain.enums import UserRole
from src.domain.repositories.base import IRepository


class IUserRepository(IRepository[User]):
    """Repository interface for User entities."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_role(
        self,
        role: UserRole,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """Get users by role.

        Args:
            role: User role
            limit: Maximum number of users
            offset: Number of users to skip

        Returns:
            List of users with specified role
        """
        ...

    @abstractmethod
    async def get_active_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all active users.

        Args:
            limit: Maximum number of users
            offset: Number of users to skip

        Returns:
            List of active users
        """
        ...

    @abstractmethod
    async def email_exists(self, email: str, exclude_id: UUID | None = None) -> bool:
        """Check if email is already registered.

        Args:
            email: Email to check
            exclude_id: User ID to exclude (for updates)

        Returns:
            True if email exists, False otherwise
        """
        ...
