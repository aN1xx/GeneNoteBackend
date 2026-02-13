"""Variant entity."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from src.domain.enums import ACMGClassification, VariantType


@dataclass
class GermlineVariant:
    """Domain entity representing a germline genetic variant."""

    # Genomic coordinates
    chromosome: str
    position: int
    ref: str
    alt: str

    # Gene information
    gene: str

    id: UUID = field(default_factory=uuid4)

    # Variant details
    variant_type: VariantType = VariantType.UNKNOWN
    transcript: str = ""
    exon_intron: str | None = None
    hgvs: str | None = None

    # Population statistics
    hetero_num: int = 0  # Number of heterozygous carriers
    homo_num: int = 0  # Number of homozygous carriers
    sample_num: int = 0  # Total number of samples analyzed

    # Annotation
    pop_freq_gnomad: Decimal | None = None
    acmg_classification: ACMGClassification = ACMGClassification.NOT_CLASSIFIED

    # Changelog for ACMG classification changes
    changelog: str | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate variant data."""
        if not self.chromosome:
            msg = "Chromosome cannot be empty"
            raise ValueError(msg)
        if self.position < 1:
            msg = "Position must be positive"
            raise ValueError(msg)
        if not self.ref:
            msg = "Reference allele cannot be empty"
            raise ValueError(msg)
        if not self.alt:
            msg = "Alternate allele cannot be empty"
            raise ValueError(msg)

    @property
    def variant_name(self) -> str:
        """Generate variant name in standard format."""
        return f"chr{self.chromosome}-{self.position}-{self.ref}-{self.alt}"

    @property
    def frequency(self) -> Decimal:
        """Calculate allele frequency in analyzed samples."""
        if self.sample_num == 0:
            return Decimal("0")
        total_alleles = 2 * self.sample_num
        variant_alleles = self.hetero_num + 2 * self.homo_num
        return Decimal(variant_alleles) / Decimal(total_alleles)

    @property
    def is_snv(self) -> bool:
        """Check if variant is a single nucleotide variant."""
        return len(self.ref) == 1 and len(self.alt) == 1

    @property
    def is_indel(self) -> bool:
        """Check if variant is an insertion or deletion."""
        return len(self.ref) != len(self.alt)

    def is_pathogenic(self) -> bool:
        """Check if variant is classified as pathogenic."""
        return self.acmg_classification.is_pathogenic()

    def is_benign(self) -> bool:
        """Check if variant is classified as benign."""
        return self.acmg_classification.is_benign()

    def update_statistics(self, is_heterozygous: bool) -> None:
        """Update variant statistics with new observation."""
        if is_heterozygous:
            self.hetero_num += 1
        else:
            self.homo_num += 1
        self.sample_num += 1
        self.updated_at = datetime.utcnow()

    def annotate(
        self,
        acmg_classification: ACMGClassification,
        variant_type: VariantType | None = None,
        pop_freq_gnomad: Decimal | None = None,
    ) -> None:
        """Annotate variant with classification and additional information."""
        self.acmg_classification = acmg_classification
        if variant_type is not None:
            self.variant_type = variant_type
        if pop_freq_gnomad is not None:
            self.pop_freq_gnomad = pop_freq_gnomad
        self.updated_at = datetime.utcnow()

    def update_acmg_with_changelog(
        self,
        new_classification: ACMGClassification,
    ) -> None:
        """Update ACMG classification and record the change in changelog.

        Args:
            new_classification: New ACMG classification value
        """
        from zoneinfo import ZoneInfo

        old_classification = self.acmg_classification

        # Only record if classification actually changed
        if old_classification != new_classification:
            # Format timestamp in UTC+5 (Kazakhstan time)
            now = datetime.now(ZoneInfo("Asia/Almaty"))
            timestamp = now.strftime("%d.%m.%Y в %H:%M:%S")

            # Build changelog entry
            entry = (
                f"{timestamp} значение ACMG было изменено "
                f'с "{old_classification.value}" на "{new_classification.value}"'
            )

            # Append to existing changelog or create new
            if self.changelog:
                self.changelog = f"{self.changelog}\n{entry}"
            else:
                self.changelog = entry

            # Update the classification
            self.acmg_classification = new_classification
            self.updated_at = datetime.utcnow()


@dataclass
class RawVariant:
    """Domain entity representing a raw (unannotated) variant from pipeline."""

    # Genomic coordinates
    chromosome: str
    position: int
    ref: str
    alt: str
    gene: str

    id: UUID = field(default_factory=uuid4)
    sample_id: UUID | None = None

    # Variant details
    variant_type: VariantType = VariantType.UNKNOWN
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

    # Database lookups
    variant_db_num: int = 0
    variant_db_hetero_num: int = 0
    variant_db_homo_num: int = 0
    artifact_db_num: int = 0

    # Annotation (to be filled by geneticist)
    pop_freq_gnomad: Decimal | None = None
    acmg_classification: ACMGClassification | None = None
    is_variant: bool | None = None
    is_artifact: bool | None = None

    @property
    def variant_name(self) -> str:
        """Generate variant name in standard format."""
        return f"chr{self.chromosome}-{self.position}-{self.ref}-{self.alt}"

    @property
    def is_heterozygous(self) -> bool:
        """Check if variant is heterozygous."""
        return "гетерозигота" in self.genotype.lower() or "het" in self.genotype.lower()

    @property
    def is_homozygous(self) -> bool:
        """Check if variant is homozygous."""
        return "гомозигота" in self.genotype.lower() or "hom" in self.genotype.lower()

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
        """Check if variant has been annotated."""
        return self.is_variant is not None or self.is_artifact is not None

    def mark_as_variant(
        self,
        acmg_classification: ACMGClassification,
        variant_type: VariantType | None = None,
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

    def mark_as_artifact(self) -> None:
        """Mark as artifact (false positive)."""
        self.is_variant = False
        self.is_artifact = True
