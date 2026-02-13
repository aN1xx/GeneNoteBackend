"""Sample-related domain exceptions."""

from src.domain.exceptions.base import (
    BusinessRuleViolationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
)


class SampleNotFoundError(EntityNotFoundError):
    """Raised when a sample is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__("Sample", identifier)


class SampleAlreadyExistsError(EntityAlreadyExistsError):
    """Raised when trying to create a sample that already exists."""

    def __init__(self, identifier: str) -> None:
        super().__init__("Sample", identifier)


class SampleNotReadyForProcessingError(BusinessRuleViolationError):
    """Raised when sample is not ready for processing."""

    def __init__(self, sample_id: str, reason: str) -> None:
        self.sample_id = sample_id
        super().__init__(
            rule="Sample must be ready for processing",
            details=f"Sample {sample_id}: {reason}",
        )


class SampleNotReadyForAnnotationError(BusinessRuleViolationError):
    """Raised when sample is not ready for annotation."""

    def __init__(self, sample_id: str, current_status: str) -> None:
        self.sample_id = sample_id
        super().__init__(
            rule="Sample must be awaiting annotation",
            details=f"Sample {sample_id} is in status '{current_status}'",
        )
