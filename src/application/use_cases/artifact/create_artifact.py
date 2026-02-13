"""Create artifact use case."""

from dataclasses import dataclass
from uuid import uuid4

from src.application.dto.artifact import ArtifactResponse, CreateArtifactRequest
from src.domain.entities import GermlineArtifact
from src.domain.exceptions import EntityAlreadyExistsError
from src.domain.repositories import IUnitOfWork


@dataclass
class CreateArtifactUseCase:
    """Use case for creating new artifact record."""

    uow: IUnitOfWork

    async def execute(self, request: CreateArtifactRequest) -> ArtifactResponse:
        """Create new artifact.

        Args:
            request: Artifact creation request

        Returns:
            Created artifact response

        Raises:
            EntityAlreadyExistsError: If artifact already exists at coordinates
        """
        async with self.uow:
            # Check if artifact already exists
            exists = await self.uow.artifacts.artifact_exists(
                chromosome=request.chromosome,
                position=request.position,
                ref=request.ref,
                alt=request.alt,
            )

            if exists:
                raise EntityAlreadyExistsError(
                    entity_type="Artifact",
                    identifier=f"chr{request.chromosome}:{request.position}",
                )

            # Create artifact
            artifact = GermlineArtifact(
                id=uuid4(),
                chromosome=request.chromosome,
                position=request.position,
                ref=request.ref,
                alt=request.alt,
                occurrence_num=1,
                sample_num=1,
            )

            await self.uow.artifacts.save(artifact)
            await self.uow.commit()

            return ArtifactResponse.from_entity(artifact)
