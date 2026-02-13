"""Variant name value object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VariantName:
    """Immutable value object representing a variant name.

    Standard format: chr{chrom}-{pos}-{ref}-{alt}
    Example: chr13-32316435-G-A
    """

    chromosome: str
    position: int
    ref: str
    alt: str

    def __post_init__(self) -> None:
        """Validate variant name components."""
        from src.domain.value_objects.chromosome import Chromosome
        from src.domain.value_objects.genomic_position import GenomicPosition

        # Validate and normalize chromosome
        chrom = Chromosome(self.chromosome)
        object.__setattr__(self, "chromosome", chrom.value)

        # Validate position
        GenomicPosition(self.position)

        # Validate ref and alt alleles
        if not self.ref or not self.ref.strip():
            msg = "Reference allele cannot be empty"
            raise ValueError(msg)
        if not self.alt or not self.alt.strip():
            msg = "Alternate allele cannot be empty"
            raise ValueError(msg)

        # Normalize alleles (uppercase)
        object.__setattr__(self, "ref", self.ref.upper().strip())
        object.__setattr__(self, "alt", self.alt.upper().strip())

        # Validate alleles contain only valid characters
        valid_chars = set("ACGTN-")
        if not set(self.ref).issubset(valid_chars):
            msg = f"Invalid characters in reference allele: {self.ref}"
            raise ValueError(msg)
        if not set(self.alt).issubset(valid_chars):
            msg = f"Invalid characters in alternate allele: {self.alt}"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Return variant name in standard format."""
        return f"chr{self.chromosome}-{self.position}-{self.ref}-{self.alt}"

    def __repr__(self) -> str:
        """Return string representation."""
        return f"VariantName('{self}')"

    @property
    def is_snv(self) -> bool:
        """Check if variant is a single nucleotide variant."""
        return len(self.ref) == 1 and len(self.alt) == 1

    @property
    def is_insertion(self) -> bool:
        """Check if variant is an insertion."""
        return len(self.ref) < len(self.alt)

    @property
    def is_deletion(self) -> bool:
        """Check if variant is a deletion."""
        return len(self.ref) > len(self.alt)

    @property
    def is_indel(self) -> bool:
        """Check if variant is an indel (insertion or deletion)."""
        return self.is_insertion or self.is_deletion

    @classmethod
    def from_string(cls, value: str) -> "VariantName":
        """Parse variant name from string format 'chr-pos-ref-alt'."""
        parts = value.replace("chr", "").split("-")
        if len(parts) != 4:
            msg = f"Invalid variant name format: {value}. Expected chr-pos-ref-alt"
            raise ValueError(msg)

        chrom, pos_str, ref, alt = parts
        try:
            pos = int(pos_str)
        except ValueError as e:
            msg = f"Invalid position in variant name: {pos_str}"
            raise ValueError(msg) from e

        return cls(chromosome=chrom, position=pos, ref=ref, alt=alt)

    @classmethod
    def from_components(
        cls,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> "VariantName":
        """Create variant name from individual components."""
        return cls(chromosome=chromosome, position=position, ref=ref, alt=alt)
