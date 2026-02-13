"""HGVS notation value object."""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HGVSNotation:
    """Immutable value object representing HGVS nomenclature.

    HGVS (Human Genome Variation Society) notation is the standard
    for describing sequence variants.

    Examples:
        - c.5114T>C (coding DNA)
        - c.5114T>C(p.Leu1705Pro) (with protein effect)
        - c.68-7del (intronic deletion)
        - c.4563A>G(p.Leu1521=) (synonymous)
    """

    value: str

    # Pattern for basic HGVS validation
    HGVS_PATTERN: re.Pattern[str] = re.compile(
        r"^[cgmnpr]\."  # Reference sequence type
        r"[\-\d\*\+]+"  # Position (can include intronic positions like -7)
        r"[A-Za-z>_\d\(\)=]+"  # Variant description
    )

    def __post_init__(self) -> None:
        """Validate HGVS notation."""
        if not self.value or not self.value.strip():
            msg = "HGVS notation cannot be empty"
            raise ValueError(msg)

        normalized = self.value.strip()
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        """Return HGVS notation string."""
        return self.value

    def __repr__(self) -> str:
        """Return string representation."""
        return f"HGVSNotation('{self.value}')"

    @property
    def reference_type(self) -> str | None:
        """Get reference sequence type (c, g, m, n, p, r).

        c = coding DNA
        g = genomic
        m = mitochondrial
        n = non-coding RNA
        p = protein
        r = RNA
        """
        if self.value and len(self.value) >= 2 and self.value[1] == ".":
            return self.value[0].lower()
        return None

    @property
    def is_coding(self) -> bool:
        """Check if notation describes coding DNA change."""
        return self.reference_type == "c"

    @property
    def is_protein(self) -> bool:
        """Check if notation describes protein change."""
        return self.reference_type == "p"

    @property
    def coding_notation(self) -> str | None:
        """Extract coding notation (before protein effect)."""
        if "(" in self.value:
            return self.value.split("(")[0]
        return self.value

    @property
    def protein_effect(self) -> str | None:
        """Extract protein effect from notation if present."""
        match = re.search(r"\(p\.([^)]+)\)", self.value)
        if match:
            return f"p.{match.group(1)}"
        return None

    @property
    def is_synonymous(self) -> bool:
        """Check if variant is synonymous (protein notation ends with =)."""
        protein = self.protein_effect
        return protein is not None and protein.endswith("=")

    @classmethod
    def from_string(cls, value: str | None) -> "HGVSNotation | None":
        """Create HGVSNotation from string, returning None for invalid input."""
        if value is None or not value.strip():
            return None
        try:
            return cls(value=value)
        except ValueError:
            return None
