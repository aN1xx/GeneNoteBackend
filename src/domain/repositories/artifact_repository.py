"""Artifact repository interface."""

from abc import abstractmethod
from uuid import UUID

from src.domain.entities import GermlineArtifact
from src.domain.repositories.base import IRepository


class IArtifactRepository(IRepository[GermlineArtifact]):
    """Repository interface for GermlineArtifact entities."""

    @abstractmethod
    async def get_by_coordinates(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> GermlineArtifact | None:
        """Get artifact by genomic coordinates.

        Args:
            chromosome: Chromosome (1-22, X, Y, MT)
            position: Genomic position (1-based)
            ref: Reference allele
            alt: Alternate allele

        Returns:
            Artifact if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_artifact_name(self, artifact_name: str) -> GermlineArtifact | None:
        """Get artifact by artifact name (chr-pos-ref-alt).

        Args:
            artifact_name: Artifact name in format chr{chrom}-{pos}-{ref}-{alt}

        Returns:
            Artifact if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_frequent(
        self,
        threshold: float = 0.1,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GermlineArtifact]:
        """Get frequently occurring artifacts.

        Args:
            threshold: Minimum occurrence rate (default 10%)
            limit: Maximum number of artifacts
            offset: Number of artifacts to skip

        Returns:
            List of frequent artifacts
        """
        ...

    @abstractmethod
    async def save_many(
        self,
        artifacts: list[GermlineArtifact],
    ) -> list[GermlineArtifact]:
        """Save multiple artifacts in bulk.

        Args:
            artifacts: List of artifacts to save

        Returns:
            List of saved artifacts
        """
        ...

    @abstractmethod
    async def artifact_exists(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> bool:
        """Check if artifact exists by coordinates.

        Args:
            chromosome: Chromosome
            position: Position
            ref: Reference allele
            alt: Alternate allele

        Returns:
            True if artifact exists
        """
        ...

    @abstractmethod
    async def increment_occurrence(
        self,
        artifact_id: UUID,
    ) -> GermlineArtifact | None:
        """Increment occurrence count for an artifact.

        Args:
            artifact_id: Artifact UUID

        Returns:
            Updated artifact if found, None otherwise
        """
        ...
