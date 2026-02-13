"""Authentication and authorization exceptions."""

from src.domain.exceptions.base import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    ForbiddenError,
    UnauthorizedError,
)


class UserNotFoundError(EntityNotFoundError):
    """Raised when a user is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__("User", identifier)


class UserAlreadyExistsError(EntityAlreadyExistsError):
    """Raised when trying to create a user that already exists."""

    def __init__(self, identifier: str) -> None:
        super().__init__("User", identifier)


class InvalidCredentialsError(UnauthorizedError):
    """Raised when credentials are invalid."""

    def __init__(self) -> None:
        super().__init__(action="authenticate", reason="Invalid email or password")


class InvalidTokenError(UnauthorizedError):
    """Raised when JWT token is invalid."""

    def __init__(self, reason: str = "Token is invalid or expired") -> None:
        super().__init__(action="authenticate", reason=reason)


class InsufficientPermissionsError(ForbiddenError):
    """Raised when user lacks required permissions."""

    def __init__(self, action: str, required_role: str | None = None) -> None:
        reason = f"Required role: {required_role}" if required_role else None
        super().__init__(action=action, reason=reason)


class UserInactiveError(ForbiddenError):
    """Raised when user account is inactive."""

    def __init__(self) -> None:
        super().__init__(
            action="access the system",
            reason="User account is deactivated",
        )
