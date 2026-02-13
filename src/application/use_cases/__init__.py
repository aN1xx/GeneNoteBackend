"""Application use cases."""

from src.application.use_cases.auth import (
    LoginUseCase,
    RefreshTokenUseCase,
    RegisterUseCase,
)
from src.application.use_cases.patient import (
    CreatePatientUseCase,
    GetPatientByRequestIdUseCase,
    GetPatientUseCase,
    ListPatientsUseCase,
    SearchPatientsUseCase,
)
from src.application.use_cases.pipeline import (
    GetActivePipelineRunsUseCase,
    GetPipelineRunsBySampleUseCase,
    GetPipelineRunsByStatusUseCase,
    GetPipelineRunUseCase,
    StartPipelineUseCase,
)
from src.application.use_cases.sample import (
    CreateSampleUseCase,
    GetAwaitingAnnotationSamplesUseCase,
    GetSampleByCodeUseCase,
    GetSamplesByPatientUseCase,
    GetSampleUseCase,
)
from src.application.use_cases.variant import (
    GetPathogenicVariantsUseCase,
    GetVariantByNameUseCase,
    GetVariantUseCase,
    SearchVariantsUseCase,
)

__all__ = [
    # Patient
    "CreatePatientUseCase",
    # Sample
    "CreateSampleUseCase",
    # Pipeline
    "GetActivePipelineRunsUseCase",
    "GetAwaitingAnnotationSamplesUseCase",
    # Variant
    "GetPathogenicVariantsUseCase",
    "GetPatientByRequestIdUseCase",
    "GetPatientUseCase",
    "GetPipelineRunUseCase",
    "GetPipelineRunsBySampleUseCase",
    "GetPipelineRunsByStatusUseCase",
    "GetSampleByCodeUseCase",
    "GetSampleUseCase",
    "GetSamplesByPatientUseCase",
    "GetVariantByNameUseCase",
    "GetVariantUseCase",
    "ListPatientsUseCase",
    # Auth
    "LoginUseCase",
    "RefreshTokenUseCase",
    "RegisterUseCase",
    "SearchPatientsUseCase",
    "SearchVariantsUseCase",
    "StartPipelineUseCase",
]
