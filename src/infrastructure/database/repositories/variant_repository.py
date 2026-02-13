"""Variant repository implementation."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import GermlineVariant
from src.domain.enums import ACMGClassification
from src.domain.repositories import IVariantRepository
from src.infrastructure.database.models import VariantModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemyVariantRepository(
    SQLAlchemyRepository[VariantModel, GermlineVariant],
    IVariantRepository,
):
    """SQLAlchemy implementation of Variant repository."""

    model_class = VariantModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_coordinates(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> GermlineVariant | None:
        """Get variant by genomic coordinates."""
        # Normalize chromosome
        chrom = chromosome.upper().replace("CHR", "")
        stmt = select(VariantModel).where(
            VariantModel.chromosome == chrom,
            VariantModel.position == position,
            VariantModel.ref == ref.upper(),
            VariantModel.alt == alt.upper(),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_variant_name(self, variant_name: str) -> GermlineVariant | None:
        """Get variant by variant name (chr-pos-ref-alt)."""
        # Parse variant name
        parts = variant_name.replace("chr", "").split("-")
        if len(parts) != 4:
            return None
        chrom, pos_str, ref, alt = parts
        try:
            pos = int(pos_str)
        except ValueError:
            return None
        return await self.get_by_coordinates(chrom, pos, ref, alt)

    async def get_by_gene(
        self,
        gene: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GermlineVariant]:
        """Get variants by gene name."""
        stmt = (
            select(VariantModel)
            .where(VariantModel.gene == gene.upper())
            .order_by(VariantModel.position)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_classification(
        self,
        classification: ACMGClassification,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GermlineVariant]:
        """Get variants by ACMG classification."""
        stmt = (
            select(VariantModel)
            .where(VariantModel.acmg_classification == classification)
            .order_by(VariantModel.gene, VariantModel.position)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_pathogenic(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GermlineVariant]:
        """Get pathogenic and likely pathogenic variants."""
        stmt = (
            select(VariantModel)
            .where(
                VariantModel.acmg_classification.in_(
                    [ACMGClassification.PATHOGENIC, ACMGClassification.LIKELY_PATHOGENIC]
                )
            )
            .order_by(VariantModel.gene, VariantModel.position)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def search(
        self,
        query: str,
        limit: int = 50,
    ) -> list[GermlineVariant]:
        """Search variants by gene name or variant name."""
        stmt = (
            select(VariantModel)
            .where(
                or_(
                    VariantModel.gene.ilike(f"%{query}%"),
                    VariantModel.hgvs.ilike(f"%{query}%"),
                )
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save_many(
        self,
        variants: list[GermlineVariant],
    ) -> list[GermlineVariant]:
        """Save multiple variants in bulk."""
        models = [self._to_model(v) for v in variants]
        for model in models:
            await self._session.merge(model)
        await self._session.flush()
        return variants

    async def variant_exists(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> bool:
        """Check if variant exists by coordinates."""
        chrom = chromosome.upper().replace("CHR", "")
        stmt = select(func.count()).where(
            VariantModel.chromosome == chrom,
            VariantModel.position == position,
            VariantModel.ref == ref.upper(),
            VariantModel.alt == alt.upper(),
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count is not None and count > 0

    def _to_entity(self, model: VariantModel) -> GermlineVariant:
        """Convert ORM model to domain entity."""
        return GermlineVariant(
            id=model.id,
            chromosome=model.chromosome,
            position=model.position,
            ref=model.ref,
            alt=model.alt,
            gene=model.gene,
            variant_type=model.variant_type,
            transcript=model.transcript,
            exon_intron=model.exon_intron,
            hgvs=model.hgvs,
            hetero_num=model.hetero_num,
            homo_num=model.homo_num,
            sample_num=model.sample_num,
            pop_freq_gnomad=model.pop_freq_gnomad,
            acmg_classification=model.acmg_classification,
            changelog=model.changelog,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: GermlineVariant) -> VariantModel:
        """Convert domain entity to ORM model."""
        return VariantModel(
            id=entity.id,
            chromosome=entity.chromosome.upper().replace("CHR", ""),
            position=entity.position,
            ref=entity.ref.upper(),
            alt=entity.alt.upper(),
            gene=entity.gene.upper(),
            variant_type=entity.variant_type,
            transcript=entity.transcript,
            exon_intron=entity.exon_intron,
            hgvs=entity.hgvs,
            hetero_num=entity.hetero_num,
            homo_num=entity.homo_num,
            sample_num=entity.sample_num,
            pop_freq_gnomad=entity.pop_freq_gnomad,
            acmg_classification=entity.acmg_classification,
            changelog=entity.changelog,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
