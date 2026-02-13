"""Variant-related domain exceptions."""

from src.domain.exceptions.base import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    ValidationError,
)


class VariantNotFoundError(EntityNotFoundError):
    """Raised when a variant is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__("Variant", identifier)


class VariantAlreadyExistsError(EntityAlreadyExistsError):
    """Raised when trying to create a variant that already exists."""

    def __init__(self, identifier: str) -> None:
        super().__init__("Variant", identifier)


class InvalidChromosomeError(ValidationError):
    """Raised when chromosome value is invalid."""

    def __init__(self, chromosome: str) -> None:
        self.chromosome = chromosome
        super().__init__(
            message=f"Invalid chromosome: {chromosome}. Must be 1-22, X, Y, or MT",
            field="chromosome",
        )


class InvalidPositionError(ValidationError):
    """Raised when genomic position is invalid."""

    def __init__(self, position: int, reason: str | None = None) -> None:
        self.position = position
        message = f"Invalid genomic position: {position}"
        if reason:
            message += f". {reason}"
        super().__init__(message=message, field="position")


class InvalidVariantNameError(ValidationError):
    """Raised when variant name format is invalid."""

    def __init__(self, variant_name: str) -> None:
        self.variant_name = variant_name
        super().__init__(
            message=f"Invalid variant name format: {variant_name}. Expected chr-pos-ref-alt",
            field="variant_name",
        )


class ArtifactNotFoundError(EntityNotFoundError):
    """Raised when an artifact is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__("Artifact", identifier)
