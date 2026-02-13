"""Variant DTOs."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field

from src.domain.enums import ACMGClassification, VariantType  # noqa: TC001

if TYPE_CHECKING:
    from src.domain.entities.sample_variant import SampleVariant


class VariantResponse(BaseModel):
    """Variant response DTO."""

    id: UUID
    chromosome: str
    position: int
    ref: str
    alt: str
    gene: str
    variant_name: str
    variant_type: VariantType
    transcript: str
    exon_intron: str | None
    hgvs: str | None
    hetero_num: int
    homo_num: int
    sample_num: int
    frequency: Decimal
    pop_freq_gnomad: Decimal | None
    acmg_classification: ACMGClassification
    is_pathogenic: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VariantListResponse(BaseModel):
    """Variant list response DTO with pagination."""

    items: list[VariantResponse]
    total: int
    limit: int
    offset: int


class VariantSearchRequest(BaseModel):
    """Variant search request DTO."""

    gene: str | None = None
    chromosome: str | None = None
    classification: ACMGClassification | None = None
    query: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class AnnotateVariantRequest(BaseModel):
    """Annotate variant request DTO."""

    acmg_classification: ACMGClassification
    variant_type: VariantType | None = None
    pop_freq_gnomad: Decimal | None = None


class RawVariantResponse(BaseModel):
    """Raw variant response DTO (for annotation view)."""

    id: UUID
    sample_id: UUID | None
    chromosome: str
    position: int
    ref: str
    alt: str
    gene: str
    variant_name: str
    variant_type: VariantType
    transcript: str
    exon_intron: str | None
    hgvs: str | None
    depth: int
    genotype: str
    variant_caller: str
    caller_count: int
    variant_db_num: int
    variant_db_hetero_num: int
    variant_db_homo_num: int
    artifact_db_num: int
    pop_freq_gnomad: Decimal | None
    acmg_classification: ACMGClassification | None
    is_variant: bool | None
    is_artifact: bool | None
    is_annotated: bool

    class Config:
        from_attributes = True


class SampleVariantResponse(BaseModel):
    """Sample variant response DTO (from pipeline output)."""

    id: UUID
    sample_id: UUID
    chromosome: str
    position: int
    ref: str
    alt: str
    gene: str
    variant_name: str
    variant_type: str | None
    transcript: str
    exon_intron: str | None
    hgvs: str | None
    depth: int
    genotype: str
    variant_caller: str
    caller_count: int
    gatk_depth: int | None
    gatk_allele_depth: int | None
    gatk_allele_fraction: Decimal | None
    variant_db_num: int
    variant_db_hetero_num: int
    variant_db_homo_num: int
    artifact_db_num: int
    pop_freq_gnomad: Decimal | None
    acmg_classification: ACMGClassification | None
    is_variant: bool | None
    is_artifact: bool | None
    is_annotated: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_entity(cls, entity: SampleVariant) -> SampleVariantResponse:
        """Create response from domain entity."""
        return cls(
            id=entity.id,
            sample_id=entity.sample_id,
            chromosome=entity.chromosome,
            position=entity.position,
            ref=entity.ref,
            alt=entity.alt,
            gene=entity.gene,
            variant_name=entity.variant_name,
            variant_type=entity.variant_type,
            transcript=entity.transcript,
            exon_intron=entity.exon_intron,
            hgvs=entity.hgvs,
            depth=entity.depth,
            genotype=entity.genotype,
            variant_caller=entity.variant_caller,
            caller_count=entity.caller_count,
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
            is_annotated=entity.is_annotated(),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @classmethod
    def from_entity_with_live_data(
        cls,
        entity: SampleVariant,
        variant_db_num: int,
        variant_db_hetero_num: int,
        variant_db_homo_num: int,
        artifact_db_num: int,
        acmg_classification: ACMGClassification | None = None,
        variant_type: VariantType | None = None,
        pop_freq_gnomad: Decimal | None = None,
    ) -> SampleVariantResponse:
        """Create response from domain entity with live database data.

        Args:
            entity: SampleVariant domain entity
            variant_db_num: Live count from germline_variants (hetero + homo)
            variant_db_hetero_num: Live hetero count from germline_variants
            variant_db_homo_num: Live homo count from germline_variants
            artifact_db_num: Live count from germline_artifacts
            acmg_classification: ACMG from germline_variants (overrides entity value if set)
            variant_type: Variant type from germline_variants (overrides entity value if set)
            pop_freq_gnomad: gnomAD frequency from germline_variants (overrides entity value if set)
        """
        # Use live values if available, otherwise fall back to entity's values
        effective_acmg = (
            acmg_classification if acmg_classification is not None else entity.acmg_classification
        )
        effective_variant_type = (
            variant_type.value if variant_type is not None else entity.variant_type
        )
        effective_pop_freq = (
            pop_freq_gnomad if pop_freq_gnomad is not None else entity.pop_freq_gnomad
        )

        return cls(
            id=entity.id,
            sample_id=entity.sample_id,
            chromosome=entity.chromosome,
            position=entity.position,
            ref=entity.ref,
            alt=entity.alt,
            gene=entity.gene,
            variant_name=entity.variant_name,
            variant_type=effective_variant_type,
            transcript=entity.transcript,
            exon_intron=entity.exon_intron,
            hgvs=entity.hgvs,
            depth=entity.depth,
            genotype=entity.genotype,
            variant_caller=entity.variant_caller,
            caller_count=entity.caller_count,
            gatk_depth=entity.gatk_depth,
            gatk_allele_depth=entity.gatk_allele_depth,
            gatk_allele_fraction=entity.gatk_allele_fraction,
            variant_db_num=variant_db_num,
            variant_db_hetero_num=variant_db_hetero_num,
            variant_db_homo_num=variant_db_homo_num,
            artifact_db_num=artifact_db_num,
            pop_freq_gnomad=effective_pop_freq,
            acmg_classification=effective_acmg,
            is_variant=entity.is_variant,
            is_artifact=entity.is_artifact,
            is_annotated=entity.is_annotated(),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class SampleVariantListResponse(BaseModel):
    """Sample variant list response DTO."""

    items: list[SampleVariantResponse]
    total: int
    annotated_count: int


class AnnotateSampleVariantRequest(BaseModel):
    """Request to annotate a sample variant."""

    is_variant: bool = Field(..., description="True if confirmed variant, False if artifact")
    acmg_classification: ACMGClassification | None = Field(
        None,
        description="ACMG classification (required if is_variant=True)",
    )
    variant_type: str | None = Field(None, description="Variant type")
    pop_freq_gnomad: Decimal | None = Field(None, description="gnomAD population frequency")


class RawVariantListResponse(BaseModel):
    """Raw variant list response DTO."""

    items: list[RawVariantResponse]
    total: int


class AnnotateRawVariantRequest(BaseModel):
    """Annotate raw variant request DTO."""

    is_variant: bool
    acmg_classification: ACMGClassification | None = None
    variant_type: VariantType | None = None
    pop_freq_gnomad: Decimal | None = None


class BatchAnnotateItem(BaseModel):
    """Single item for batch annotation."""

    variant_id: UUID
    is_variant: bool = Field(..., description="True if confirmed variant, False if artifact")
    acmg_classification: ACMGClassification | None = Field(
        None,
        description="ACMG classification (required if is_variant=True)",
    )
    variant_type: str | None = Field(None, description="Variant type")
    pop_freq_gnomad: Decimal | None = Field(None, description="gnomAD population frequency")


class BatchAnnotateRequest(BaseModel):
    """Batch annotation request DTO."""

    annotations: list[BatchAnnotateItem] = Field(
        ...,
        min_length=1,
        description="List of variant annotations",
    )


class BatchAnnotateResponse(BaseModel):
    """Batch annotation response DTO."""

    updated_count: int
    failed_count: int
    errors: list[str] | None = None
