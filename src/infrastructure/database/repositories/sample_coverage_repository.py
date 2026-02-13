"""Sample coverage repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import SampleCoverage
from src.domain.repositories.sample_coverage_repository import ISampleCoverageRepository
from src.infrastructure.database.models import SampleCoverageModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemySampleCoverageRepository(
    SQLAlchemyRepository[SampleCoverageModel, SampleCoverage],
    ISampleCoverageRepository,
):
    """SQLAlchemy implementation of SampleCoverage repository."""

    model_class = SampleCoverageModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_sample_id(self, sample_id: UUID) -> SampleCoverage | None:
        """Get coverage data for a sample."""
        stmt = select(SampleCoverageModel).where(SampleCoverageModel.sample_id == sample_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def upsert(self, coverage: SampleCoverage) -> SampleCoverage:
        """Insert or update coverage data for a sample."""
        model = self._to_model(coverage)
        merged = await self._session.merge(model)
        await self._session.flush()
        return self._to_entity(merged)

    def _to_entity(self, model: SampleCoverageModel) -> SampleCoverage:
        """Convert ORM model to domain entity."""
        return SampleCoverage(
            id=model.id,
            sample_id=UUID(str(model.sample_id)),
            depth_0x=model.depth_0x,
            depth_5x=model.depth_5x,
            depth_30x=model.depth_30x,
            depth_50x=model.depth_50x,
            depth_100x=model.depth_100x,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: SampleCoverage) -> SampleCoverageModel:
        """Convert domain entity to ORM model."""
        return SampleCoverageModel(
            id=entity.id,
            sample_id=entity.sample_id,
            depth_0x=entity.depth_0x,
            depth_5x=entity.depth_5x,
            depth_30x=entity.depth_30x,
            depth_50x=entity.depth_50x,
            depth_100x=entity.depth_100x,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
