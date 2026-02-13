"""Sample coverage repository interface."""

from abc import abstractmethod
from uuid import UUID

from src.domain.entities import SampleCoverage
from src.domain.repositories.base import IRepository


class ISampleCoverageRepository(IRepository[SampleCoverage]):
    """Repository interface for sample coverage data."""

    @abstractmethod
    async def get_by_sample_id(self, sample_id: UUID) -> SampleCoverage | None:
        """Get coverage data for a sample.

        Args:
            sample_id: Sample UUID

        Returns:
            SampleCoverage if found, None otherwise
        """
        ...

    @abstractmethod
    async def upsert(self, coverage: SampleCoverage) -> SampleCoverage:
        """Insert or update coverage data for a sample.

        Args:
            coverage: Coverage data to save

        Returns:
            Saved coverage data
        """
        ...
