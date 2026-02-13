"""Pipeline API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.application.dto.pipeline import (
    PipelineRunListResponse,
    PipelineRunResponse,
    StartPipelineRequest,
)
from src.application.use_cases.pipeline import (
    GetActivePipelineRunsUseCase,
    GetPipelineRunsBySampleUseCase,
    GetPipelineRunsByStatusUseCase,
    GetPipelineRunUseCase,
    StartPipelineUseCase,
)
from src.domain.enums import PipelineStatus, PipelineType
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.infrastructure.kafka import get_kafka_producer
from src.presentation.dependencies import CurrentUser, LaborantUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


def get_uow() -> SQLAlchemyUnitOfWork:
    """Get Unit of Work instance."""
    return SQLAlchemyUnitOfWork(async_session_factory)


@router.post(
    "/start",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start pipeline",
    description="Start a new pipeline run for a sample",
)
async def start_pipeline(
    request: StartPipelineRequest,
    current_user: LaborantUser,
) -> PipelineRunResponse:
    """Start a new pipeline run.

    - Laborants can start variant calling pipelines
    - Geneticists can start report generation pipelines
    """
    try:
        kafka_producer = await get_kafka_producer()
    except Exception as e:
        logger.warning(f"Kafka producer unavailable: {e}")
        kafka_producer = None

    use_case = StartPipelineUseCase(uow=get_uow(), kafka_producer=kafka_producer)
    return await use_case.execute(request)


@router.get(
    "/by-status/{status}",
    response_model=PipelineRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pipelines by status",
    description="Get pipeline runs filtered by status",
)
async def get_pipelines_by_status(
    status: PipelineStatus,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PipelineRunListResponse:
    """Get pipeline runs by status."""
    use_case = GetPipelineRunsByStatusUseCase(uow=get_uow())
    return await use_case.execute(status=status, limit=limit, offset=offset)


@router.get(
    "/by-sample/{sample_id}",
    response_model=PipelineRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pipelines by sample",
    description="Get all pipeline runs for a sample",
)
async def get_pipelines_by_sample(
    sample_id: UUID,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PipelineRunListResponse:
    """Get pipeline runs by sample ID."""
    use_case = GetPipelineRunsBySampleUseCase(uow=get_uow())
    return await use_case.execute(sample_id=sample_id, limit=limit, offset=offset)


@router.get(
    "/active/{sample_id}",
    response_model=PipelineRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active pipelines",
    description="Get active pipeline runs for a sample",
)
async def get_active_pipelines(
    sample_id: UUID,
    current_user: CurrentUser,
    pipeline_type: PipelineType | None = Query(default=None),
) -> PipelineRunListResponse:
    """Get active pipeline runs for a sample."""
    use_case = GetActivePipelineRunsUseCase(uow=get_uow())
    return await use_case.execute(sample_id=sample_id, pipeline_type=pipeline_type)


@router.get(
    "/{pipeline_id}",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pipeline run",
    description="Get pipeline run by ID",
)
async def get_pipeline_run(
    pipeline_id: UUID,
    current_user: CurrentUser,
) -> PipelineRunResponse:
    """Get pipeline run by ID."""
    use_case = GetPipelineRunUseCase(uow=get_uow())
    return await use_case.execute(pipeline_id)


@router.post(
    "/{pipeline_id}/cancel",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel pipeline",
    description="Cancel a running pipeline",
)
async def cancel_pipeline(
    pipeline_id: UUID,
    current_user: LaborantUser,
) -> PipelineRunResponse:
    """Cancel a pipeline run."""
    uow = get_uow()

    async with uow:
        run = await uow.pipelines.get_by_id(pipeline_id)
        if not run:
            from src.domain.exceptions import PipelineRunNotFoundError

            raise PipelineRunNotFoundError(str(pipeline_id))

        run.cancel()
        await uow.pipelines.save(run)
        await uow.commit()

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
