"""Genomic position value object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GenomicPosition:
    """Immutable value object representing a genomic position.

    Position is 1-based as per standard genomic conventions (VCF, GFF, etc.).
    """

    value: int

    # Human genome GRCh38 max position (approximately)
    MAX_POSITION: int = 250_000_000

    def __post_init__(self) -> None:
        """Validate position value."""
        if not isinstance(self.value, int):
            msg = f"Position must be an integer, got {type(self.value).__name__}"
            raise TypeError(msg)
        if self.value < 1:
            msg = f"Position must be positive (1-based), got {self.value}"
            raise ValueError(msg)
        if self.value > self.MAX_POSITION:
            msg = f"Position {self.value} exceeds maximum {self.MAX_POSITION}"
            raise ValueError(msg)

    def __str__(self) -> str:
        """Return position as string."""
        return str(self.value)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"GenomicPosition({self.value})"

    def __int__(self) -> int:
        """Return position as integer."""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "GenomicPosition":
        """Create GenomicPosition from string."""
        try:
            return cls(value=int(value.strip()))
        except ValueError as e:
            msg = f"Cannot parse genomic position from '{value}'"
            raise ValueError(msg) from e


@dataclass(frozen=True, slots=True)
class GenomicCoordinate:
    """Immutable value object representing a full genomic coordinate.

    Combines chromosome and position into a single object.
    """

    chromosome: str
    position: int

    def __post_init__(self) -> None:
        """Validate coordinate components."""
        from src.domain.value_objects.chromosome import Chromosome

        # Validate chromosome
        chrom = Chromosome(self.chromosome)
        object.__setattr__(self, "chromosome", chrom.value)

        # Validate position
        pos = GenomicPosition(self.position)
        object.__setattr__(self, "position", pos.value)

    def __str__(self) -> str:
        """Return coordinate in standard format (chr:pos)."""
        return f"chr{self.chromosome}:{self.position}"

    def __repr__(self) -> str:
        """Return string representation."""
        return f"GenomicCoordinate('{self.chromosome}', {self.position})"

    @classmethod
    def from_string(cls, value: str) -> "GenomicCoordinate":
        """Parse coordinate from string format 'chr:pos' or 'chr-pos'."""
        # Try different separators
        for sep in (":", "-", "_"):
            if sep in value:
                parts = value.split(sep, 1)
                if len(parts) == 2:
                    chrom, pos = parts
                    return cls(chromosome=chrom, position=int(pos))

        msg = f"Cannot parse genomic coordinate from '{value}'"
        raise ValueError(msg)
