"""Domain exceptions."""

from src.domain.exceptions.auth import (
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserInactiveError,
    UserNotFoundError,
)
from src.domain.exceptions.base import (
    BusinessRuleViolationError,
    DomainError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
)
from src.domain.exceptions.patient import PatientAlreadyExistsError, PatientNotFoundError
from src.domain.exceptions.pipeline import (
    PipelineAlreadyRunningError,
    PipelineExecutionError,
    PipelineNotCancellableError,
    PipelineRunNotFoundError,
)
from src.domain.exceptions.report import ReportNotFoundError
from src.domain.exceptions.sample import (
    SampleAlreadyExistsError,
    SampleNotFoundError,
    SampleNotReadyForAnnotationError,
    SampleNotReadyForProcessingError,
)
from src.domain.exceptions.variant import (
    ArtifactNotFoundError,
    InvalidChromosomeError,
    InvalidPositionError,
    InvalidVariantNameError,
    VariantAlreadyExistsError,
    VariantNotFoundError,
)

__all__ = [
    # Variant
    "ArtifactNotFoundError",
    # Base
    "BusinessRuleViolationError",
    "DomainError",
    "EntityAlreadyExistsError",
    "EntityNotFoundError",
    "ForbiddenError",
    # Auth
    "InsufficientPermissionsError",
    "InvalidChromosomeError",
    "InvalidCredentialsError",
    "InvalidPositionError",
    "InvalidTokenError",
    "InvalidVariantNameError",
    # Patient
    "PatientAlreadyExistsError",
    "PatientNotFoundError",
    # Pipeline
    "PipelineAlreadyRunningError",
    "PipelineExecutionError",
    "PipelineNotCancellableError",
    "PipelineRunNotFoundError",
    # Report
    "ReportNotFoundError",
    # Sample
    "SampleAlreadyExistsError",
    "SampleNotFoundError",
    "SampleNotReadyForAnnotationError",
    "SampleNotReadyForProcessingError",
    "UnauthorizedError",
    "UserAlreadyExistsError",
    "UserInactiveError",
    "UserNotFoundError",
    "ValidationError",
    "VariantAlreadyExistsError",
    "VariantNotFoundError",
]
