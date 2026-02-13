"""Artifact DTOs for API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateArtifactRequest(BaseModel):
    """Request for creating new artifact."""

    chromosome: str = Field(..., description="Chromosome (1-22, X, Y, MT)")
    position: int = Field(..., ge=1, description="Genomic position (1-based)")
    ref: str = Field(..., min_length=1, description="Reference allele")
    alt: str = Field(..., min_length=1, description="Alternate allele")


class ArtifactResponse(BaseModel):
    """Response for artifact entity."""

    id: UUID
    chromosome: str
    position: int
    ref: str
    alt: str
    artifact_name: str
    occurrence_num: int
    sample_num: int
    occurrence_rate: float
    is_frequent: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, entity) -> "ArtifactResponse":
        """Create response from entity."""
        return cls(
            id=entity.id,
            chromosome=entity.chromosome,
            position=entity.position,
            ref=entity.ref,
            alt=entity.alt,
            artifact_name=entity.artifact_name,
            occurrence_num=entity.occurrence_num,
            sample_num=entity.sample_num,
            occurrence_rate=entity.occurrence_rate,
            is_frequent=entity.is_frequent(),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class ArtifactListResponse(BaseModel):
    """Response for list of artifacts."""

    items: list[ArtifactResponse]
    total: int
    limit: int
    offset: int
