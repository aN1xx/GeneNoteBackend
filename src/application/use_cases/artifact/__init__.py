"""Artifact use cases."""

from src.application.use_cases.artifact.create_artifact import CreateArtifactUseCase
from src.application.use_cases.artifact.get_artifact import (
    GetArtifactByCoordinatesUseCase,
    GetArtifactUseCase,
    GetFrequentArtifactsUseCase,
)
from src.application.use_cases.artifact.record_occurrence import (
    RecordArtifactOccurrenceUseCase,
)

__all__ = [
    "CreateArtifactUseCase",
    "GetArtifactByCoordinatesUseCase",
    "GetArtifactUseCase",
    "GetFrequentArtifactsUseCase",
    "RecordArtifactOccurrenceUseCase",
]
