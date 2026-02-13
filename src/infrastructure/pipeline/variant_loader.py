"""Variant loader service for importing variants to database."""

import logging
from uuid import UUID, uuid4

from src.domain.entities import GermlineArtifact, GermlineVariant, RawVariant
from src.domain.repositories import IUnitOfWork

logger = logging.getLogger(__name__)


class VariantLoader:
    """Service for loading variants into database."""

    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def load_raw_variants(
        self,
        raw_variants: list[RawVariant],
        sample_id: UUID,
        patient_id: UUID,
    ) -> dict:
        """Load raw variants and update variant/artifact databases.

        Args:
            raw_variants: List of raw variants from pipeline
            sample_id: Sample UUID
            patient_id: Patient UUID

        Returns:
            Dict with loading statistics
        """
        stats = {
            "total": len(raw_variants),
            "new_variants": 0,
            "updated_variants": 0,
            "new_artifacts": 0,
            "updated_artifacts": 0,
            "errors": 0,
        }

        async with self._uow:
            for raw in raw_variants:
                try:
                    await self._process_raw_variant(raw, patient_id, stats)
                except Exception as e:
                    logger.error(f"Error processing variant {raw.variant_name}: {e}")
                    stats["errors"] += 1

            await self._uow.commit()

        logger.info(f"Variant loading complete: {stats}")
        return stats

    async def _process_raw_variant(
        self,
        raw: RawVariant,
        patient_id: UUID,
        stats: dict,
    ) -> None:
        """Process a single raw variant.

        Args:
            raw: Raw variant to process
            patient_id: Patient UUID
            stats: Statistics dict to update
        """
        # Check if variant exists in database
        existing = await self._uow.variants.get_by_coordinates(
            chromosome=raw.chromosome,
            position=raw.position,
            ref=raw.ref,
            alt=raw.alt,
        )

        is_heterozygous = raw.is_heterozygous

        if existing:
            # Update statistics for existing variant
            existing.update_statistics(is_heterozygous)
            await self._uow.variants.save(existing)
            stats["updated_variants"] += 1

            # Link patient to variant (if not already linked)
            # This would be done via PatientVariant model
            logger.debug(f"Updated variant: {existing.variant_name}")
        else:
            # Create new variant entry
            new_variant = GermlineVariant(
                id=uuid4(),
                chromosome=raw.chromosome,
                position=raw.position,
                ref=raw.ref,
                alt=raw.alt,
                gene=raw.gene,
                variant_type=raw.variant_type,
                transcript=raw.transcript,
                exon_intron=raw.exon_intron,
                hgvs=raw.hgvs,
                hetero_num=1 if is_heterozygous else 0,
                homo_num=0 if is_heterozygous else 1,
                sample_num=1,
            )
            await self._uow.variants.save(new_variant)
            stats["new_variants"] += 1
            logger.debug(f"Created new variant: {new_variant.variant_name}")

        # Check/update artifact database based on frequency
        await self._check_artifact(raw, stats)

    async def _check_artifact(self, raw: RawVariant, stats: dict) -> None:
        """Check if variant should be tracked as potential artifact.

        Args:
            raw: Raw variant
            stats: Statistics dict
        """
        # If variant appears frequently in artifact database, track it
        if raw.artifact_db_num > 0:
            existing_artifact = await self._uow.artifacts.get_by_coordinates(
                chromosome=raw.chromosome,
                position=raw.position,
                ref=raw.ref,
                alt=raw.alt,
            )

            if existing_artifact:
                await self._uow.artifacts.increment_occurrence(existing_artifact.id)
                stats["updated_artifacts"] += 1
            # Create new artifact entry if occurrence is high
            elif raw.artifact_db_num >= 3:  # Threshold for new artifact
                new_artifact = GermlineArtifact(
                    id=uuid4(),
                    chromosome=raw.chromosome,
                    position=raw.position,
                    ref=raw.ref,
                    alt=raw.alt,
                    occurrence_num=raw.artifact_db_num,
                    sample_num=1,
                )
                await self._uow.artifacts.save(new_artifact)
                stats["new_artifacts"] += 1

    async def update_variant_annotation(
        self,
        variant_id: UUID,
        acmg_classification,
        variant_type=None,
        pop_freq_gnomad=None,
    ) -> GermlineVariant | None:
        """Update variant with annotation.

        Args:
            variant_id: Variant UUID
            acmg_classification: ACMG classification
            variant_type: Optional variant type
            pop_freq_gnomad: Optional gnomAD frequency

        Returns:
            Updated variant or None
        """
        async with self._uow:
            variant = await self._uow.variants.get_by_id(variant_id)
            if variant:
                variant.annotate(
                    acmg_classification=acmg_classification,
                    variant_type=variant_type,
                    pop_freq_gnomad=pop_freq_gnomad,
                )
                await self._uow.variants.save(variant)
                await self._uow.commit()
                return variant
            return None

    async def mark_as_artifact(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> GermlineArtifact:
        """Mark a variant position as artifact.

        Args:
            chromosome: Chromosome
            position: Position
            ref: Reference allele
            alt: Alternate allele

        Returns:
            Created or updated artifact
        """
        async with self._uow:
            existing = await self._uow.artifacts.get_by_coordinates(
                chromosome=chromosome,
                position=position,
                ref=ref,
                alt=alt,
            )

            if existing:
                await self._uow.artifacts.increment_occurrence(existing.id)
                artifact = existing
            else:
                artifact = GermlineArtifact(
                    id=uuid4(),
                    chromosome=chromosome,
                    position=position,
                    ref=ref,
                    alt=alt,
                    occurrence_num=1,
                    sample_num=1,
                )
                await self._uow.artifacts.save(artifact)

            await self._uow.commit()
            return artifact
