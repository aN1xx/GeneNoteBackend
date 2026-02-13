"""Patient-related domain exceptions."""

from src.domain.exceptions.base import EntityAlreadyExistsError, EntityNotFoundError


class PatientNotFoundError(EntityNotFoundError):
    """Raised when a patient is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__("Patient", identifier)


class PatientAlreadyExistsError(EntityAlreadyExistsError):
    """Raised when trying to create a patient that already exists."""

    def __init__(self, identifier: str) -> None:
        super().__init__("Patient", identifier)
