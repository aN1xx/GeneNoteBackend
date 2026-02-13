"""Sample variant entity - raw variant from pipeline output."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from src.domain.enums import ACMGClassification


@dataclass
class SampleVariant:
    """Domain entity representing a raw variant from pipeline for a specific sample.

    This stores the variant data before and during annotation by geneticist.
    """

    # Required fields
    sample_id: UUID
    chromosome: str
    position: int
    ref: str
    alt: str
    gene: str

    id: UUID = field(default_factory=uuid4)

    # Variant details
    variant_type: str | None = None  # From pipeline or filled by geneticist
    transcript: str = ""
    exon_intron: str | None = None
    hgvs: str | None = None

    # Sequencing metrics
    depth: int = 0
    genotype: str = ""  # "гетерозигота" or "гомозигота"

    # Variant caller information
    variant_caller: str = ""  # e.g., "gatk,ngsep,xatlas"
    gatk_depth: int | None = None
    gatk_allele_depth: int | None = None
    gatk_allele_fraction: Decimal | None = None

    # Database lookups (pre-filled from variants/artifacts databases)
    variant_db_num: int = 0
    variant_db_hetero_num: int = 0
    variant_db_homo_num: int = 0
    artifact_db_num: int = 0

    # Annotation fields (filled by geneticist)
    pop_freq_gnomad: Decimal | None = None
    acmg_classification: ACMGClassification | None = None

    # Geneticist decision (required for annotation completion)
    is_variant: bool | None = None
    is_artifact: bool | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def variant_name(self) -> str:
        """Generate variant name in standard format."""
        return f"chr{self.chromosome}-{self.position}-{self.ref}-{self.alt}"

    @property
    def is_heterozygous(self) -> bool:
        """Check if variant is heterozygous."""
        gt_lower = self.genotype.lower()
        return "гетерозигота" in gt_lower or "het" in gt_lower

    @property
    def is_homozygous(self) -> bool:
        """Check if variant is homozygous."""
        gt_lower = self.genotype.lower()
        return "гомозигота" in gt_lower or "hom" in gt_lower

    @property
    def callers(self) -> list[str]:
        """Get list of variant callers that detected this variant."""
        if not self.variant_caller:
            return []
        return [c.strip() for c in self.variant_caller.split(",")]

    @property
    def caller_count(self) -> int:
        """Get number of variant callers that detected this variant."""
        return len(self.callers)

    def is_annotated(self) -> bool:
        """Check if variant has been annotated by geneticist."""
        return self.is_variant is not None or self.is_artifact is not None

    def mark_as_variant(
        self,
        acmg_classification: ACMGClassification,
        variant_type: str | None = None,
        pop_freq_gnomad: Decimal | None = None,
    ) -> None:
        """Mark as true variant with annotation."""
        self.is_variant = True
        self.is_artifact = False
        self.acmg_classification = acmg_classification
        if variant_type is not None:
            self.variant_type = variant_type
        if pop_freq_gnomad is not None:
            self.pop_freq_gnomad = pop_freq_gnomad
        self.updated_at = datetime.utcnow()

    def mark_as_artifact(self) -> None:
        """Mark as artifact (false positive)."""
        self.is_variant = False
        self.is_artifact = True
        self.updated_at = datetime.utcnow()
