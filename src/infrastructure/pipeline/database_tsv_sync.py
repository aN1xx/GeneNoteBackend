"""Service for synchronizing PostgreSQL database with TSV files.

Exports GermlineVariants and GermlineArtifacts from PostgreSQL to TSV files
used by the Snakemake pipeline for variant/artifact lookups.
"""

import csv
import logging
from decimal import Decimal

from src.domain.entities import GermlineArtifact, GermlineVariant
from src.domain.repositories import IUnitOfWork
from src.infrastructure.pipeline.pipeline_service import PipelineConfig

logger = logging.getLogger(__name__)


class DatabaseTsvSyncService:
    """Service for syncing PostgreSQL data to TSV files for pipeline."""

    # Column order for GermlineVariants_DataBase.tsv
    VARIANTS_COLUMNS = [
        "VariantName",
        "hetero_num",
        "homo_num",
        "sample_num",
        "freq",
        "chrom",
        "pos_GRCh38",
        "ref",
        "alt",
    ]

    # Column order for GermlineArtifacts_DataBase.tsv
    ARTIFACTS_COLUMNS = [
        "ArtifactName",
        "chrom",
        "pos_GRCh38",
        "ref",
        "alt",
        "occurrence_num",
        "sample_num",
    ]

    def __init__(self, config: PipelineConfig | None = None) -> None:
        """Initialize service with pipeline config.

        Args:
            config: Pipeline configuration with TSV paths.
                   If None, uses default from settings.
        """
        self.config = config or PipelineConfig.from_settings()

    async def sync_variants_to_tsv(self, uow: IUnitOfWork) -> int:
        """Export all GermlineVariants from PostgreSQL to TSV.

        Args:
            uow: Unit of Work for database access

        Returns:
            Number of variants exported
        """
        async with uow:
            # Get total count first
            total = await uow.variants.count()
            if total == 0:
                logger.warning("No variants found in database to export")
                return 0
            # Get all variants (use total as limit to get everything)
            variants = await uow.variants.get_all(limit=total, offset=0)

        if not variants:
            logger.warning("No variants found in database to export")
            return 0

        # Ensure directory exists
        self.config.variants_db.parent.mkdir(parents=True, exist_ok=True)

        # Write TSV file
        with open(self.config.variants_db, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.VARIANTS_COLUMNS, delimiter="\t")
            writer.writeheader()

            for variant in variants:
                row = self._variant_to_row(variant)
                writer.writerow(row)

        logger.info(f"Exported {len(variants)} variants to {self.config.variants_db}")
        return len(variants)

    async def sync_artifacts_to_tsv(self, uow: IUnitOfWork) -> int:
        """Export all GermlineArtifacts from PostgreSQL to TSV.

        Args:
            uow: Unit of Work for database access

        Returns:
            Number of artifacts exported
        """
        async with uow:
            # Get total count first
            total = await uow.artifacts.count()
            if total == 0:
                logger.warning("No artifacts found in database to export")
                return 0
            # Get all artifacts (use total as limit to get everything)
            artifacts = await uow.artifacts.get_all(limit=total, offset=0)

        if not artifacts:
            logger.warning("No artifacts found in database to export")
            return 0

        # Ensure directory exists
        self.config.artifacts_db.parent.mkdir(parents=True, exist_ok=True)

        # Write TSV file
        with open(self.config.artifacts_db, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.ARTIFACTS_COLUMNS, delimiter="\t")
            writer.writeheader()

            for artifact in artifacts:
                row = self._artifact_to_row(artifact)
                writer.writerow(row)

        logger.info(f"Exported {len(artifacts)} artifacts to {self.config.artifacts_db}")
        return len(artifacts)

    async def sync_all(self, uow: IUnitOfWork) -> dict:
        """Sync both variants and artifacts to TSV files.

        Args:
            uow: Unit of Work for database access

        Returns:
            Dict with sync statistics
        """
        variants_count = await self.sync_variants_to_tsv(uow)
        artifacts_count = await self.sync_artifacts_to_tsv(uow)

        return {
            "variants_exported": variants_count,
            "artifacts_exported": artifacts_count,
            "variants_path": str(self.config.variants_db),
            "artifacts_path": str(self.config.artifacts_db),
        }

    def _variant_to_row(self, variant: GermlineVariant) -> dict:
        """Convert GermlineVariant entity to TSV row dict.

        Args:
            variant: GermlineVariant entity

        Returns:
            Dict with TSV column values
        """
        # Calculate frequency: (hetero + 2*homo) / (2 * sample_num)
        freq = self._calculate_frequency(variant.hetero_num, variant.homo_num, variant.sample_num)

        return {
            "VariantName": variant.variant_name,
            "hetero_num": variant.hetero_num,
            "homo_num": variant.homo_num,
            "sample_num": variant.sample_num,
            "freq": f"{freq:.3f}",
            "chrom": variant.chromosome,
            "pos_GRCh38": variant.position,
            "ref": variant.ref,
            "alt": variant.alt,
        }

    def _artifact_to_row(self, artifact: GermlineArtifact) -> dict:
        """Convert GermlineArtifact entity to TSV row dict.

        Args:
            artifact: GermlineArtifact entity

        Returns:
            Dict with TSV column values
        """
        return {
            "ArtifactName": artifact.artifact_name,
            "chrom": artifact.chromosome,
            "pos_GRCh38": artifact.position,
            "ref": artifact.ref,
            "alt": artifact.alt,
            "occurrence_num": artifact.occurrence_num,
            "sample_num": artifact.sample_num,
        }

    def _calculate_frequency(self, hetero_num: int, homo_num: int, sample_num: int) -> Decimal:
        """Calculate allele frequency.

        Formula: (hetero + 2*homo) / (2 * sample_num)

        Args:
            hetero_num: Number of heterozygous carriers
            homo_num: Number of homozygous carriers
            sample_num: Total samples analyzed

        Returns:
            Allele frequency as Decimal
        """
        if sample_num == 0:
            return Decimal("0")
        total_alleles = 2 * sample_num
        variant_alleles = hetero_num + 2 * homo_num
        return Decimal(variant_alleles) / Decimal(total_alleles)
