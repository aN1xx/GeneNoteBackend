"""Patient repository interface."""

from abc import abstractmethod
from datetime import date
from uuid import UUID

from src.domain.entities import Patient
from src.domain.repositories.base import IRepository


class IPatientRepository(IRepository[Patient]):
    """Repository interface for Patient entities."""

    @abstractmethod
    async def get_by_request_id(self, request_id: str) -> Patient | None:
        """Get patient by request ID.

        Args:
            request_id: Unique request identifier

        Returns:
            Patient if found, None otherwise
        """
        ...

    @abstractmethod
    async def search_by_name(
        self,
        name: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Patient]:
        """Search patients by name (partial match).

        Args:
            name: Name to search
            limit: Maximum number of patients
            offset: Number of patients to skip

        Returns:
            List of matching patients
        """
        ...

    @abstractmethod
    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Patient]:
        """Get patients created within date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of patients
            offset: Number of patients to skip

        Returns:
            List of patients
        """
        ...

    @abstractmethod
    async def get_with_variants(self, patient_id: UUID) -> Patient | None:
        """Get patient with their variant IDs loaded.

        Args:
            patient_id: Patient UUID

        Returns:
            Patient with variants if found, None otherwise
        """
        ...

    @abstractmethod
    async def request_id_exists(
        self,
        request_id: str,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if request ID already exists.

        Args:
            request_id: Request ID to check
            exclude_id: Patient ID to exclude (for updates)

        Returns:
            True if exists, False otherwise
        """
        ...
