"""Parser for variant table output from Snakemake pipeline.

Parses the {sample}_variants_raw.tsv file produced by make_VariantTable.py
"""

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from src.domain.entities import SampleVariant
from src.domain.enums import ACMGClassification


@dataclass
class RawVariantRow:
    """Raw variant row from pipeline output TSV."""

    chrom: str
    pos_grch38: int
    ref: str
    alt: str
    gene: str
    variant_type: str | None
    transcript: str
    exon_intron: str | None
    hgvs_variant_name: str | None
    depth: int
    genotype: str
    pop_freq_gnomad: Decimal | None
    acmg_classification: str | None
    variant_caller: str
    gatk_depth: int | None
    gatk_allele_depth: int | None
    gatk_allele_fraction: Decimal | None
    variant_db_num: int
    variant_db_hetero_num: int
    variant_db_homo_num: int
    artifact_db_num: int
    is_variant: bool | None
    is_artifact: bool | None


class VariantTableParser:
    """Parser for variant table TSV files from pipeline output."""

    # Column mapping from pipeline output to our fields
    COLUMN_MAPPING = {
        "chrom": "chrom",
        "pos_GRCh38": "pos_grch38",
        "ref": "ref",
        "alt": "alt",
        "gene": "gene",
        "variant_type": "variant_type",
        "transcript": "transcript",
        "exon/intron": "exon_intron",
        "HGVS_VariantName": "hgvs_variant_name",
        "depth": "depth",
        "genotype": "genotype",
        "PopFreq_GNOMAD_v3.1.2": "pop_freq_gnomad",
        "ACMG_classification": "acmg_classification",
        "variant_caller": "variant_caller",
        "gatk_depth": "gatk_depth",
        "gatk_allele_depth": "gatk_allele_depth",
        "gatk_allele_fraction": "gatk_allele_fraction",
        "variant_db_num": "variant_db_num",
        "variant_db_hetero_num": "variant_db_hetero_num",
        "variant_db_homo_num": "variant_db_homo_num",
        "artifact_db_num": "artifact_db_num",
        "is_variant": "is_variant",
        "is_artifact": "is_artifact",
    }

    # ACMG classification mapping from Russian to enum
    ACMG_MAPPING = {
        "Патогенный": ACMGClassification.PATHOGENIC,
        "Вероятно патогенный": ACMGClassification.LIKELY_PATHOGENIC,
        "Вариант неясного значения": ACMGClassification.VUS,
        "Вариант неясного клинического значения": ACMGClassification.VUS,
        "Вероятно доброкачественный": ACMGClassification.LIKELY_BENIGN,
        "Доброкачественный": ACMGClassification.BENIGN,
    }

    def parse_file(self, filepath: Path, sample_id: UUID) -> list[SampleVariant]:
        """Parse variant table TSV file and return list of SampleVariant entities.

        Args:
            filepath: Path to the variants TSV file
            sample_id: UUID of the sample these variants belong to

        Returns:
            List of SampleVariant domain entities
        """
        variants = []

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")

            for row in reader:
                raw_variant = self._parse_row(row)
                sample_variant = self._to_sample_variant(raw_variant, sample_id)
                variants.append(sample_variant)

        return variants

    def _parse_row(self, row: dict) -> RawVariantRow:
        """Parse a single row from the TSV file."""
        return RawVariantRow(
            chrom=self._clean_chrom(row.get("chrom", "")),
            pos_grch38=self._parse_int(row.get("pos_GRCh38", "0")),
            ref=row.get("ref", ""),
            alt=row.get("alt", ""),
            gene=row.get("gene", ""),
            variant_type=row.get("variant_type") or None,
            transcript=row.get("transcript", ""),
            exon_intron=row.get("exon/intron") or None,
            hgvs_variant_name=row.get("HGVS_VariantName") or None,
            depth=self._parse_int(row.get("depth", "0")),
            genotype=row.get("genotype", ""),
            pop_freq_gnomad=self._parse_decimal(row.get("PopFreq_GNOMAD_v3.1.2")),
            acmg_classification=row.get("ACMG_classification") or None,
            variant_caller=row.get("variant_caller", ""),
            gatk_depth=self._parse_int_optional(row.get("gatk_depth")),
            gatk_allele_depth=self._parse_int_optional(row.get("gatk_allele_depth")),
            gatk_allele_fraction=self._parse_decimal(row.get("gatk_allele_fraction")),
            variant_db_num=self._parse_int(row.get("variant_db_num", "0")),
            variant_db_hetero_num=self._parse_int(row.get("variant_db_hetero_num", "0")),
            variant_db_homo_num=self._parse_int(row.get("variant_db_homo_num", "0")),
            artifact_db_num=self._parse_int(row.get("artifact_db_num", "0")),
            is_variant=self._parse_bool(row.get("is_variant")),
            is_artifact=self._parse_bool(row.get("is_artifact")),
        )

    def _to_sample_variant(self, raw: RawVariantRow, sample_id: UUID) -> SampleVariant:
        """Convert raw variant row to SampleVariant entity."""
        acmg = None
        if raw.acmg_classification:
            acmg = self.ACMG_MAPPING.get(raw.acmg_classification)

        return SampleVariant(
            id=uuid4(),
            sample_id=sample_id,
            chromosome=raw.chrom,
            position=raw.pos_grch38,
            ref=raw.ref,
            alt=raw.alt,
            gene=raw.gene,
            variant_type=raw.variant_type,
            transcript=raw.transcript,
            exon_intron=raw.exon_intron,
            hgvs=raw.hgvs_variant_name,
            depth=raw.depth,
            genotype=raw.genotype,
            variant_caller=raw.variant_caller,
            gatk_depth=raw.gatk_depth,
            gatk_allele_depth=raw.gatk_allele_depth,
            gatk_allele_fraction=raw.gatk_allele_fraction,
            variant_db_num=raw.variant_db_num,
            variant_db_hetero_num=raw.variant_db_hetero_num,
            variant_db_homo_num=raw.variant_db_homo_num,
            artifact_db_num=raw.artifact_db_num,
            pop_freq_gnomad=raw.pop_freq_gnomad,
            acmg_classification=acmg,
            is_variant=raw.is_variant,
            is_artifact=raw.is_artifact,
        )

    def _clean_chrom(self, chrom: str) -> str:
        """Clean chromosome string (remove 'chr' prefix if present)."""
        return chrom.upper().replace("CHR", "")

    def _parse_int(self, value: str | None) -> int:
        """Parse integer value, defaulting to 0."""
        if not value or value.strip() == "":
            return 0
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def _parse_int_optional(self, value: str | None) -> int | None:
        """Parse optional integer value."""
        if not value or value.strip() == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def _parse_decimal(self, value: str | None) -> Decimal | None:
        """Parse decimal value."""
        if not value or value.strip() == "":
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _parse_bool(self, value: str | None) -> bool | None:
        """Parse boolean value from various formats."""
        if not value or value.strip() == "":
            return None
        value_lower = value.strip().lower()
        if value_lower in ("1", "true", "yes", "да"):
            return True
        if value_lower in ("0", "false", "no", "нет"):
            return False
        return None
