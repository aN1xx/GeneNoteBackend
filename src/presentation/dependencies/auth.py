"""Authentication dependencies for FastAPI."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.domain.entities import User
from src.domain.enums import UserRole
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.infrastructure.security import JWTService, TokenPayload

# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


def get_jwt_service() -> JWTService:
    """Get JWT service instance."""
    return JWTService()


def get_unit_of_work() -> SQLAlchemyUnitOfWork:
    """Get Unit of Work instance."""
    return SQLAlchemyUnitOfWork(async_session_factory)


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> TokenPayload:
    """Extract and validate JWT token from request.

    Args:
        credentials: HTTP Bearer credentials
        jwt_service: JWT service instance

    Returns:
        Token payload

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = jwt_service.verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user(
    token_payload: Annotated[TokenPayload, Depends(get_token_payload)],
    uow: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
) -> User:
    """Get current authenticated user.

    Args:
        token_payload: Validated token payload
        uow: Unit of Work instance

    Returns:
        Current user entity

    Raises:
        HTTPException: If user not found or inactive
    """
    async with uow:
        user = await uow.users.get_by_id(UUID(token_payload.sub))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )

        return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Alias for get_current_user (already checks is_active)."""
    return current_user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
Token = Annotated[TokenPayload, Depends(get_token_payload)]


class RoleChecker:
    """Dependency class for role-based access control."""

    def __init__(self, allowed_roles: list[UserRole]) -> None:
        """Initialize role checker.

        Args:
            allowed_roles: List of roles that are allowed access
        """
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        current_user: CurrentUser,
    ) -> User:
        """Check if current user has required role.

        Args:
            current_user: Current authenticated user

        Returns:
            User if authorized

        Raises:
            HTTPException: If user role is not allowed
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in self.allowed_roles]}",
            )
        return current_user


# Pre-configured role checkers
require_admin = RoleChecker([UserRole.ADMIN])
require_geneticist = RoleChecker([UserRole.GENETICIST, UserRole.ADMIN])
require_laborant = RoleChecker([UserRole.LABORANT, UserRole.ADMIN])
require_any_role = RoleChecker([UserRole.LABORANT, UserRole.GENETICIST, UserRole.ADMIN])

# Dependency aliases for role checking
AdminUser = Annotated[User, Depends(require_admin)]
GeneticistUser = Annotated[User, Depends(require_geneticist)]
LaborantUser = Annotated[User, Depends(require_laborant)]
