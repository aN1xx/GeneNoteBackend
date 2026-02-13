"""Chromosome value object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chromosome:
    """Immutable value object representing a chromosome.

    Supports human chromosomes 1-22, X, Y, and MT (mitochondrial).
    """

    value: str

    VALID_CHROMOSOMES: frozenset[str] = frozenset(
        {
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
            "20",
            "21",
            "22",
            "X",
            "Y",
            "MT",
        }
    )

    def __post_init__(self) -> None:
        """Validate and normalize chromosome value."""
        normalized = self._normalize(self.value)
        if normalized not in self.VALID_CHROMOSOMES:
            msg = f"Invalid chromosome: {self.value}. Must be 1-22, X, Y, or MT."
            raise ValueError(msg)
        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize chromosome string."""
        normalized = value.upper().strip()
        # Remove 'chr' prefix if present
        if normalized.startswith("CHR"):
            normalized = normalized[3:]
        # Handle mitochondrial variants
        if normalized in ("M", "MITO", "MITOCHONDRIAL"):
            normalized = "MT"
        return normalized

    def __str__(self) -> str:
        """Return chromosome with 'chr' prefix."""
        return f"chr{self.value}"

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Chromosome('{self.value}')"

    @property
    def is_autosome(self) -> bool:
        """Check if chromosome is an autosome (1-22)."""
        return self.value.isdigit()

    @property
    def is_sex_chromosome(self) -> bool:
        """Check if chromosome is a sex chromosome (X or Y)."""
        return self.value in ("X", "Y")

    @property
    def is_mitochondrial(self) -> bool:
        """Check if chromosome is mitochondrial."""
        return self.value == "MT"

    @property
    def number(self) -> int | None:
        """Return chromosome number for autosomes, None otherwise."""
        if self.is_autosome:
            return int(self.value)
        return None

    @classmethod
    def from_string(cls, value: str) -> "Chromosome":
        """Create Chromosome from string."""
        return cls(value=value)
