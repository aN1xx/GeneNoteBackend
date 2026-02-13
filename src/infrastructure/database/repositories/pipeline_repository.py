"""Pipeline repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import PipelineRun
from src.domain.enums import PipelineStatus, PipelineType
from src.domain.repositories import IPipelineRepository
from src.infrastructure.database.models import PipelineRunModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemyPipelineRepository(
    SQLAlchemyRepository[PipelineRunModel, PipelineRun],
    IPipelineRepository,
):
    """SQLAlchemy implementation of Pipeline repository."""

    model_class = PipelineRunModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_sample_id(
        self,
        sample_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRun]:
        """Get pipeline runs by sample ID."""
        stmt = (
            select(PipelineRunModel)
            .where(PipelineRunModel.sample_id == sample_id)
            .order_by(PipelineRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_status(
        self,
        status: PipelineStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRun]:
        """Get pipeline runs by status."""
        stmt = (
            select(PipelineRunModel)
            .where(PipelineRunModel.status == status)
            .order_by(PipelineRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_type(
        self,
        pipeline_type: PipelineType,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRun]:
        """Get pipeline runs by type."""
        stmt = (
            select(PipelineRunModel)
            .where(PipelineRunModel.pipeline_type == pipeline_type)
            .order_by(PipelineRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_active_for_sample(
        self,
        sample_id: UUID,
        pipeline_type: PipelineType | None = None,
    ) -> list[PipelineRun]:
        """Get active (non-terminal) pipeline runs for a sample."""
        active_statuses = [
            PipelineStatus.PENDING,
            PipelineStatus.QUEUED,
            PipelineStatus.RUNNING,
        ]
        stmt = select(PipelineRunModel).where(
            PipelineRunModel.sample_id == sample_id,
            PipelineRunModel.status.in_(active_statuses),
        )
        if pipeline_type:
            stmt = stmt.where(PipelineRunModel.pipeline_type == pipeline_type)
        stmt = stmt.order_by(PipelineRunModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_latest_for_sample(
        self,
        sample_id: UUID,
        pipeline_type: PipelineType,
    ) -> PipelineRun | None:
        """Get the latest pipeline run of a type for a sample."""
        stmt = (
            select(PipelineRunModel)
            .where(
                PipelineRunModel.sample_id == sample_id,
                PipelineRunModel.pipeline_type == pipeline_type,
            )
            .order_by(PipelineRunModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def has_active_run(
        self,
        sample_id: UUID,
        pipeline_type: PipelineType,
    ) -> bool:
        """Check if sample has an active pipeline run of given type."""
        active_runs = await self.get_active_for_sample(sample_id, pipeline_type)
        return len(active_runs) > 0

    def _to_entity(self, model: PipelineRunModel) -> PipelineRun:
        """Convert ORM model to domain entity."""
        return PipelineRun(
            id=model.id,
            sample_id=model.sample_id,  # type: ignore[arg-type]
            pipeline_type=model.pipeline_type,
            status=model.status,
            started_at=model.started_at,
            completed_at=model.completed_at,
            output_path=model.output_path,
            error_message=model.error_message,
            progress_percent=model.progress_percent,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: PipelineRun) -> PipelineRunModel:
        """Convert domain entity to ORM model."""
        return PipelineRunModel(
            id=entity.id,
            sample_id=entity.sample_id,
            pipeline_type=entity.pipeline_type,
            status=entity.status,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            output_path=entity.output_path,
            error_message=entity.error_message,
            progress_percent=entity.progress_percent,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
