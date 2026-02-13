"""Record artifact occurrence use case."""

from dataclasses import dataclass
from uuid import uuid4

from src.application.dto.artifact import ArtifactResponse
from src.domain.entities import GermlineArtifact
from src.domain.repositories import IUnitOfWork


@dataclass
class RecordArtifactOccurrenceUseCase:
    """Use case for recording artifact occurrence when variant is marked as artifact."""

    uow: IUnitOfWork

    async def execute(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> ArtifactResponse:
        """Record artifact occurrence.

        If artifact doesn't exist, creates it. Otherwise increments occurrence count.

        Args:
            chromosome: Chromosome
            position: Genomic position
            ref: Reference allele
            alt: Alternate allele

        Returns:
            Updated or created artifact response
        """
        async with self.uow:
            artifact = await self.uow.artifacts.get_by_coordinates(
                chromosome=chromosome,
                position=position,
                ref=ref,
                alt=alt,
            )

            if artifact:
                # Increment occurrence
                artifact.record_occurrence()
                await self.uow.artifacts.save(artifact)
            else:
                # Create new artifact
                artifact = GermlineArtifact(
                    id=uuid4(),
                    chromosome=chromosome,
                    position=position,
                    ref=ref,
                    alt=alt,
                    occurrence_num=1,
                    sample_num=1,
                )
                await self.uow.artifacts.save(artifact)

            await self.uow.commit()

            return ArtifactResponse.from_entity(artifact)
