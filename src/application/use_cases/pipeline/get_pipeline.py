"""Get pipeline use cases."""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.pipeline import PipelineRunListResponse, PipelineRunResponse
from src.domain.entities import PipelineRun
from src.domain.enums import PipelineStatus, PipelineType
from src.domain.exceptions import PipelineRunNotFoundError
from src.domain.repositories import IUnitOfWork


def _to_response(run: PipelineRun) -> PipelineRunResponse:
    """Convert pipeline run entity to response DTO."""
    return PipelineRunResponse(
        id=run.id,
        sample_id=run.sample_id,
        pipeline_type=run.pipeline_type,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        output_path=run.output_path,
        error_message=run.error_message,
        progress_percent=run.progress_percent,
        duration_seconds=run.duration_seconds,
        is_terminal=run.is_terminal,
        is_active=run.is_active,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@dataclass
class GetPipelineRunUseCase:
    """Use case for getting a pipeline run by ID."""

    uow: IUnitOfWork

    async def execute(self, pipeline_id: UUID) -> PipelineRunResponse:
        """Execute get pipeline run use case.

        Args:
            pipeline_id: Pipeline run UUID

        Returns:
            Pipeline run response

        Raises:
            PipelineRunNotFoundError: If pipeline run not found
        """
        async with self.uow:
            run = await self.uow.pipelines.get_by_id(pipeline_id)

            if not run:
                raise PipelineRunNotFoundError(str(pipeline_id))

            return _to_response(run)


@dataclass
class GetPipelineRunsBySampleUseCase:
    """Use case for getting pipeline runs by sample ID."""

    uow: IUnitOfWork

    async def execute(
        self,
        sample_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> PipelineRunListResponse:
        """Execute get pipeline runs by sample use case.

        Args:
            sample_id: Sample UUID
            limit: Maximum number of runs
            offset: Number of runs to skip

        Returns:
            Pipeline run list response
        """
        async with self.uow:
            runs = await self.uow.pipelines.get_by_sample_id(
                sample_id=sample_id,
                limit=limit,
                offset=offset,
            )

            items = [_to_response(r) for r in runs]

            return PipelineRunListResponse(
                items=items,
                total=len(items),
                limit=limit,
                offset=offset,
            )


@dataclass
class GetPipelineRunsByStatusUseCase:
    """Use case for getting pipeline runs by status."""

    uow: IUnitOfWork

    async def execute(
        self,
        status: PipelineStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> PipelineRunListResponse:
        """Execute get pipeline runs by status use case.

        Args:
            status: Pipeline status to filter by
            limit: Maximum number of runs
            offset: Number of runs to skip

        Returns:
            Pipeline run list response
        """
        async with self.uow:
            runs = await self.uow.pipelines.get_by_status(
                status=status,
                limit=limit,
                offset=offset,
            )

            items = [_to_response(r) for r in runs]

            return PipelineRunListResponse(
                items=items,
                total=len(items),
                limit=limit,
                offset=offset,
            )


@dataclass
class GetActivePipelineRunsUseCase:
    """Use case for getting active pipeline runs for a sample."""

    uow: IUnitOfWork

    async def execute(
        self,
        sample_id: UUID,
        pipeline_type: PipelineType | None = None,
    ) -> PipelineRunListResponse:
        """Execute get active pipeline runs use case.

        Args:
            sample_id: Sample UUID
            pipeline_type: Optional pipeline type filter

        Returns:
            Pipeline run list response
        """
        async with self.uow:
            runs = await self.uow.pipelines.get_active_for_sample(
                sample_id=sample_id,
                pipeline_type=pipeline_type,
            )

            items = [_to_response(r) for r in runs]

            return PipelineRunListResponse(
                items=items,
                total=len(items),
                limit=100,
                offset=0,
            )
