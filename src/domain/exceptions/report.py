"""Report-related domain exceptions."""

from src.domain.exceptions.base import DomainError


class ReportNotFoundError(DomainError):
    """Report not found or not generated."""

    def __init__(self, message: str = "Report not found") -> None:
        """Initialize exception.

        Args:
            message: Error message
        """
        super().__init__(message)
