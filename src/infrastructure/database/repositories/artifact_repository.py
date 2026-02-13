"""Artifact repository implementation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import GermlineArtifact
from src.domain.repositories import IArtifactRepository
from src.infrastructure.database.models import ArtifactModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemyArtifactRepository(
    SQLAlchemyRepository[ArtifactModel, GermlineArtifact],
    IArtifactRepository,
):
    """SQLAlchemy implementation of Artifact repository."""

    model_class = ArtifactModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_coordinates(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> GermlineArtifact | None:
        """Get artifact by genomic coordinates."""
        chrom = chromosome.upper().replace("CHR", "")
        stmt = select(ArtifactModel).where(
            ArtifactModel.chromosome == chrom,
            ArtifactModel.position == position,
            ArtifactModel.ref == ref.upper(),
            ArtifactModel.alt == alt.upper(),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_artifact_name(self, artifact_name: str) -> GermlineArtifact | None:
        """Get artifact by artifact name (chr-pos-ref-alt)."""
        parts = artifact_name.replace("chr", "").split("-")
        if len(parts) != 4:
            return None
        chrom, pos_str, ref, alt = parts
        try:
            pos = int(pos_str)
        except ValueError:
            return None
        return await self.get_by_coordinates(chrom, pos, ref, alt)

    async def get_frequent(
        self,
        threshold: float = 0.1,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GermlineArtifact]:
        """Get frequently occurring artifacts."""
        # Filter where occurrence_rate >= threshold
        # occurrence_rate = occurrence_num / sample_num
        stmt = (
            select(ArtifactModel)
            .where(
                ArtifactModel.sample_num > 0,
                (ArtifactModel.occurrence_num * 1.0 / ArtifactModel.sample_num) >= threshold,
            )
            .order_by((ArtifactModel.occurrence_num * 1.0 / ArtifactModel.sample_num).desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save_many(
        self,
        artifacts: list[GermlineArtifact],
    ) -> list[GermlineArtifact]:
        """Save multiple artifacts in bulk."""
        models = [self._to_model(a) for a in artifacts]
        for model in models:
            await self._session.merge(model)
        await self._session.flush()
        return artifacts

    async def artifact_exists(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> bool:
        """Check if artifact exists by coordinates."""
        chrom = chromosome.upper().replace("CHR", "")
        stmt = select(func.count()).where(
            ArtifactModel.chromosome == chrom,
            ArtifactModel.position == position,
            ArtifactModel.ref == ref.upper(),
            ArtifactModel.alt == alt.upper(),
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count is not None and count > 0

    async def increment_occurrence(
        self,
        artifact_id: UUID,
    ) -> GermlineArtifact | None:
        """Increment occurrence count for an artifact."""
        stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.occurrence_num += 1
            await self._session.flush()
            return self._to_entity(model)
        return None

    def _to_entity(self, model: ArtifactModel) -> GermlineArtifact:
        """Convert ORM model to domain entity."""
        return GermlineArtifact(
            id=model.id,
            chromosome=model.chromosome,
            position=model.position,
            ref=model.ref,
            alt=model.alt,
            occurrence_num=model.occurrence_num,
            sample_num=model.sample_num,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: GermlineArtifact) -> ArtifactModel:
        """Convert domain entity to ORM model."""
        return ArtifactModel(
            id=entity.id,
            chromosome=entity.chromosome.upper().replace("CHR", ""),
            position=entity.position,
            ref=entity.ref.upper(),
            alt=entity.alt.upper(),
            occurrence_num=entity.occurrence_num,
            sample_num=entity.sample_num,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
