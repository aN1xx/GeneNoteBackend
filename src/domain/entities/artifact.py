"""Artifact entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class GermlineArtifact:
    """Domain entity representing a known sequencing artifact.

    Artifacts are false positive variants that repeatedly appear
    due to technical issues with sequencing or library preparation.
    """

    # Genomic coordinates
    chromosome: str
    position: int
    ref: str
    alt: str

    id: UUID = field(default_factory=uuid4)

    # Statistics
    occurrence_num: int = 0  # Number of times this artifact was observed
    sample_num: int = 0  # Total number of samples analyzed

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate artifact data."""
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
    def artifact_name(self) -> str:
        """Generate artifact name in standard format."""
        return f"chr{self.chromosome}-{self.position}-{self.ref}-{self.alt}"

    @property
    def occurrence_rate(self) -> float:
        """Calculate occurrence rate (frequency of artifact appearance)."""
        if self.sample_num == 0:
            return 0.0
        return self.occurrence_num / self.sample_num

    def is_frequent(self, threshold: float = 0.1) -> bool:
        """Check if artifact occurs frequently (above threshold).

        Args:
            threshold: Frequency threshold (default 10%)
        """
        return self.occurrence_rate >= threshold

    def record_occurrence(self) -> None:
        """Record a new occurrence of this artifact."""
        self.occurrence_num += 1
        self.updated_at = datetime.utcnow()

    def update_sample_count(self, new_sample_num: int) -> None:
        """Update total sample count."""
        self.sample_num = new_sample_num
        self.updated_at = datetime.utcnow()
