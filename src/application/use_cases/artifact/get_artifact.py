"""Get artifact use cases."""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.artifact import ArtifactListResponse, ArtifactResponse
from src.domain.exceptions import ArtifactNotFoundError
from src.domain.repositories import IUnitOfWork


@dataclass
class GetArtifactUseCase:
    """Use case for getting artifact by ID."""

    uow: IUnitOfWork

    async def execute(self, artifact_id: UUID) -> ArtifactResponse:
        """Get artifact by ID.

        Args:
            artifact_id: Artifact UUID

        Returns:
            Artifact response

        Raises:
            ArtifactNotFoundError: If artifact not found
        """
        async with self.uow:
            artifact = await self.uow.artifacts.get_by_id(artifact_id)

            if not artifact:
                raise ArtifactNotFoundError(str(artifact_id))

            return ArtifactResponse.from_entity(artifact)


@dataclass
class GetArtifactByCoordinatesUseCase:
    """Use case for getting artifact by genomic coordinates."""

    uow: IUnitOfWork

    async def execute(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> ArtifactResponse:
        """Get artifact by genomic coordinates.

        Args:
            chromosome: Chromosome
            position: Genomic position
            ref: Reference allele
            alt: Alternate allele

        Returns:
            Artifact response

        Raises:
            ArtifactNotFoundError: If artifact not found
        """
        async with self.uow:
            artifact = await self.uow.artifacts.get_by_coordinates(
                chromosome=chromosome,
                position=position,
                ref=ref,
                alt=alt,
            )

            if not artifact:
                raise ArtifactNotFoundError(f"chr{chromosome}:{position} {ref}>{alt}")

            return ArtifactResponse.from_entity(artifact)


@dataclass
class GetFrequentArtifactsUseCase:
    """Use case for getting frequently occurring artifacts."""

    uow: IUnitOfWork

    async def execute(
        self,
        threshold: float = 0.1,
        limit: int = 100,
        offset: int = 0,
    ) -> ArtifactListResponse:
        """Get frequently occurring artifacts.

        Args:
            threshold: Minimum occurrence rate (default 10%)
            limit: Maximum number of artifacts
            offset: Number of artifacts to skip

        Returns:
            List of frequent artifacts
        """
        async with self.uow:
            artifacts = await self.uow.artifacts.get_frequent(
                threshold=threshold,
                limit=limit,
                offset=offset,
            )

            return ArtifactListResponse(
                items=[ArtifactResponse.from_entity(a) for a in artifacts],
                total=len(artifacts),
                limit=limit,
                offset=offset,
            )
