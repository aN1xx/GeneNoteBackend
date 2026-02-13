"""Sample repository interface."""

from abc import abstractmethod
from uuid import UUID

from src.domain.entities import Sample
from src.domain.enums import SampleStatus
from src.domain.repositories.base import IRepository


class ISampleRepository(IRepository[Sample]):
    """Repository interface for Sample entities."""

    @abstractmethod
    async def get_by_patient_id(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Sample]:
        """Get samples by patient ID.

        Args:
            patient_id: Patient UUID
            limit: Maximum number of samples
            offset: Number of samples to skip

        Returns:
            List of samples for the patient
        """
        ...

    @abstractmethod
    async def get_by_sample_code(self, sample_code: str) -> Sample | None:
        """Get sample by sample code.

        Args:
            sample_code: Unique sample code

        Returns:
            Sample if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_status(
        self,
        status: SampleStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Sample]:
        """Get samples by status.

        Args:
            status: Sample status
            limit: Maximum number of samples
            offset: Number of samples to skip

        Returns:
            List of samples with specified status
        """
        ...

    @abstractmethod
    async def get_awaiting_annotation(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Sample]:
        """Get samples awaiting annotation.

        Args:
            limit: Maximum number of samples
            offset: Number of samples to skip

        Returns:
            List of samples awaiting annotation
        """
        ...

    @abstractmethod
    async def sample_code_exists(
        self,
        sample_code: str,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if sample code already exists.

        Args:
            sample_code: Sample code to check
            exclude_id: Sample ID to exclude (for updates)

        Returns:
            True if exists, False otherwise
        """
        ...
