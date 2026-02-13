"""Pipeline repository interface."""

from abc import abstractmethod
from uuid import UUID

from src.domain.entities import PipelineRun
from src.domain.enums import PipelineStatus, PipelineType
from src.domain.repositories.base import IRepository


class IPipelineRepository(IRepository[PipelineRun]):
    """Repository interface for PipelineRun entities."""

    @abstractmethod
    async def get_by_sample_id(
        self,
        sample_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRun]:
        """Get pipeline runs by sample ID.

        Args:
            sample_id: Sample UUID
            limit: Maximum number of runs
            offset: Number of runs to skip

        Returns:
            List of pipeline runs for the sample
        """
        ...

    @abstractmethod
    async def get_by_status(
        self,
        status: PipelineStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRun]:
        """Get pipeline runs by status.

        Args:
            status: Pipeline status
            limit: Maximum number of runs
            offset: Number of runs to skip

        Returns:
            List of pipeline runs with specified status
        """
        ...

    @abstractmethod
    async def get_by_type(
        self,
        pipeline_type: PipelineType,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRun]:
        """Get pipeline runs by type.

        Args:
            pipeline_type: Pipeline type
            limit: Maximum number of runs
            offset: Number of runs to skip

        Returns:
            List of pipeline runs of specified type
        """
        ...

    @abstractmethod
    async def get_active_for_sample(
        self,
        sample_id: UUID,
        pipeline_type: PipelineType | None = None,
    ) -> list[PipelineRun]:
        """Get active (non-terminal) pipeline runs for a sample.

        Args:
            sample_id: Sample UUID
            pipeline_type: Optional pipeline type filter

        Returns:
            List of active pipeline runs
        """
        ...

    @abstractmethod
    async def get_latest_for_sample(
        self,
        sample_id: UUID,
        pipeline_type: PipelineType,
    ) -> PipelineRun | None:
        """Get the latest pipeline run of a type for a sample.

        Args:
            sample_id: Sample UUID
            pipeline_type: Pipeline type

        Returns:
            Latest pipeline run if found, None otherwise
        """
        ...

    @abstractmethod
    async def has_active_run(
        self,
        sample_id: UUID,
        pipeline_type: PipelineType,
    ) -> bool:
        """Check if sample has an active pipeline run of given type.

        Args:
            sample_id: Sample UUID
            pipeline_type: Pipeline type

        Returns:
            True if active run exists
        """
        ...
