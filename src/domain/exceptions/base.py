"""Base domain exceptions."""


class DomainError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str = "Domain error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class EntityNotFoundError(DomainError):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, identifier: str) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} with identifier '{identifier}' not found")


class EntityAlreadyExistsError(DomainError):
    """Raised when trying to create an entity that already exists."""

    def __init__(self, entity_type: str, identifier: str) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} with identifier '{identifier}' already exists")


class ValidationError(DomainError):
    """Raised when validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        if field:
            message = f"Validation error for field '{field}': {message}"
        super().__init__(message)


class BusinessRuleViolationError(DomainError):
    """Raised when a business rule is violated."""

    def __init__(self, rule: str, details: str | None = None) -> None:
        self.rule = rule
        self.details = details
        message = f"Business rule violation: {rule}"
        if details:
            message += f". Details: {details}"
        super().__init__(message)


class UnauthorizedError(DomainError):
    """Raised when user is not authorized to perform an action."""

    def __init__(self, action: str, reason: str | None = None) -> None:
        self.action = action
        self.reason = reason
        message = f"Unauthorized to {action}"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class ForbiddenError(DomainError):
    """Raised when user is forbidden from performing an action."""

    def __init__(self, action: str, reason: str | None = None) -> None:
        self.action = action
        self.reason = reason
        message = f"Forbidden to {action}"
        if reason:
            message += f": {reason}"
        super().__init__(message)
