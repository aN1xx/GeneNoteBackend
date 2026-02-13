"""Sample variant repository implementation."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import SampleVariant
from src.domain.repositories.sample_variant_repository import ISampleVariantRepository
from src.infrastructure.database.models import SampleVariantModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemySampleVariantRepository(
    SQLAlchemyRepository[SampleVariantModel, SampleVariant],
    ISampleVariantRepository,
):
    """SQLAlchemy implementation of SampleVariant repository."""

    model_class = SampleVariantModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_sample_id(
        self,
        sample_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SampleVariant]:
        """Get all variants for a sample."""
        stmt = (
            select(SampleVariantModel)
            .where(SampleVariantModel.sample_id == sample_id)
            .order_by(SampleVariantModel.chromosome, SampleVariantModel.position)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_unannotated_by_sample(
        self,
        sample_id: UUID,
    ) -> list[SampleVariant]:
        """Get unannotated variants for a sample."""
        stmt = (
            select(SampleVariantModel)
            .where(
                SampleVariantModel.sample_id == sample_id,
                SampleVariantModel.is_variant.is_(None),
                SampleVariantModel.is_artifact.is_(None),
            )
            .order_by(SampleVariantModel.chromosome, SampleVariantModel.position)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_coordinates(
        self,
        sample_id: UUID,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> SampleVariant | None:
        """Get variant by genomic coordinates within a sample."""
        chrom = chromosome.upper().replace("CHR", "")
        stmt = select(SampleVariantModel).where(
            SampleVariantModel.sample_id == sample_id,
            SampleVariantModel.chromosome == chrom,
            SampleVariantModel.position == position,
            SampleVariantModel.ref == ref.upper(),
            SampleVariantModel.alt == alt.upper(),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_confirmed_variants(
        self,
        sample_id: UUID,
    ) -> list[SampleVariant]:
        """Get variants confirmed as true variants."""
        stmt = (
            select(SampleVariantModel)
            .where(
                SampleVariantModel.sample_id == sample_id,
                SampleVariantModel.is_variant.is_(True),
            )
            .order_by(SampleVariantModel.chromosome, SampleVariantModel.position)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_artifacts(
        self,
        sample_id: UUID,
    ) -> list[SampleVariant]:
        """Get variants marked as artifacts."""
        stmt = (
            select(SampleVariantModel)
            .where(
                SampleVariantModel.sample_id == sample_id,
                SampleVariantModel.is_artifact.is_(True),
            )
            .order_by(SampleVariantModel.chromosome, SampleVariantModel.position)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_annotated_variants(
        self,
        sample_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SampleVariant]:
        """Get all annotated variants (both confirmed variants and artifacts)."""
        from sqlalchemy import or_

        stmt = (
            select(SampleVariantModel)
            .where(
                SampleVariantModel.sample_id == sample_id,
                or_(
                    SampleVariantModel.is_variant.is_not(None),
                    SampleVariantModel.is_artifact.is_not(None),
                ),
            )
            .order_by(SampleVariantModel.chromosome, SampleVariantModel.position)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save_many(
        self,
        variants: list[SampleVariant],
    ) -> list[SampleVariant]:
        """Save multiple variants in bulk."""
        models = [self._to_model(v) for v in variants]
        for model in models:
            await self._session.merge(model)
        await self._session.flush()
        return variants

    async def count_by_sample(self, sample_id: UUID) -> int:
        """Count variants for a sample."""
        stmt = (
            select(func.count())
            .select_from(SampleVariantModel)
            .where(SampleVariantModel.sample_id == sample_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def count_annotated_by_sample(self, sample_id: UUID) -> int:
        """Count annotated variants for a sample."""
        stmt = (
            select(func.count())
            .select_from(SampleVariantModel)
            .where(
                SampleVariantModel.sample_id == sample_id,
                or_(
                    SampleVariantModel.is_variant.is_not(None),
                    SampleVariantModel.is_artifact.is_not(None),
                ),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_unique_variant_types(self) -> list[str]:
        """Get all unique variant types from database."""
        stmt = (
            select(SampleVariantModel.variant_type)
            .where(SampleVariantModel.variant_type.is_not(None))
            .distinct()
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.fetchall() if row[0]]

    def _to_entity(self, model: SampleVariantModel) -> SampleVariant:
        """Convert ORM model to domain entity."""
        return SampleVariant(
            id=model.id,
            sample_id=UUID(str(model.sample_id)),
            chromosome=model.chromosome,
            position=model.position,
            ref=model.ref,
            alt=model.alt,
            gene=model.gene,
            variant_type=model.variant_type,
            transcript=model.transcript,
            exon_intron=model.exon_intron,
            hgvs=model.hgvs,
            depth=model.depth,
            genotype=model.genotype,
            variant_caller=model.variant_caller,
            gatk_depth=model.gatk_depth,
            gatk_allele_depth=model.gatk_allele_depth,
            gatk_allele_fraction=model.gatk_allele_fraction,
            variant_db_num=model.variant_db_num,
            variant_db_hetero_num=model.variant_db_hetero_num,
            variant_db_homo_num=model.variant_db_homo_num,
            artifact_db_num=model.artifact_db_num,
            pop_freq_gnomad=model.pop_freq_gnomad,
            acmg_classification=model.acmg_classification,
            is_variant=model.is_variant,
            is_artifact=model.is_artifact,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: SampleVariant) -> SampleVariantModel:
        """Convert domain entity to ORM model."""
        return SampleVariantModel(
            id=entity.id,
            sample_id=entity.sample_id,
            chromosome=entity.chromosome.upper().replace("CHR", ""),
            position=entity.position,
            ref=entity.ref.upper(),
            alt=entity.alt.upper(),
            gene=entity.gene.upper(),
            variant_type=entity.variant_type,
            transcript=entity.transcript,
            exon_intron=entity.exon_intron,
            hgvs=entity.hgvs,
            depth=entity.depth,
            genotype=entity.genotype,
            variant_caller=entity.variant_caller,
            gatk_depth=entity.gatk_depth,
            gatk_allele_depth=entity.gatk_allele_depth,
            gatk_allele_fraction=entity.gatk_allele_fraction,
            variant_db_num=entity.variant_db_num,
            variant_db_hetero_num=entity.variant_db_hetero_num,
            variant_db_homo_num=entity.variant_db_homo_num,
            artifact_db_num=entity.artifact_db_num,
            pop_freq_gnomad=entity.pop_freq_gnomad,
            acmg_classification=entity.acmg_classification,
            is_variant=entity.is_variant,
            is_artifact=entity.is_artifact,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
