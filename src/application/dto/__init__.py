"""Application DTOs (Data Transfer Objects)."""

from src.application.dto.artifact import (
    ArtifactListResponse,
    ArtifactResponse,
    CreateArtifactRequest,
)
from src.application.dto.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
)
from src.application.dto.patient import (
    CreatePatientRequest,
    PatientListResponse,
    PatientResponse,
    PatientSearchRequest,
    UpdatePatientRequest,
)
from src.application.dto.pipeline import (
    PipelineCompletionUpdate,
    PipelineProgressUpdate,
    PipelineRunListResponse,
    PipelineRunResponse,
    StartPipelineRequest,
)
from src.application.dto.report import (
    GenerateReportResponse,
    ReportBytesResponse,
)
from src.application.dto.sample import (
    CreateSampleRequest,
    SampleListResponse,
    SampleResponse,
    UpdateSampleRequest,
    UploadFilesRequest,
    UploadFilesResponse,
)
from src.application.dto.variant import (
    AnnotateRawVariantRequest,
    AnnotateSampleVariantRequest,
    AnnotateVariantRequest,
    BatchAnnotateItem,
    BatchAnnotateRequest,
    BatchAnnotateResponse,
    RawVariantListResponse,
    RawVariantResponse,
    SampleVariantListResponse,
    SampleVariantResponse,
    VariantListResponse,
    VariantResponse,
    VariantSearchRequest,
)

__all__ = [
    # Variant
    "AnnotateRawVariantRequest",
    "AnnotateSampleVariantRequest",
    "AnnotateVariantRequest",
    # Artifact
    "ArtifactListResponse",
    "ArtifactResponse",
    "BatchAnnotateItem",
    "BatchAnnotateRequest",
    "BatchAnnotateResponse",
    # Auth
    "ChangePasswordRequest",
    "CreateArtifactRequest",
    # Patient
    "CreatePatientRequest",
    # Sample
    "CreateSampleRequest",
    # Report
    "GenerateReportResponse",
    "LoginRequest",
    "PatientListResponse",
    "PatientResponse",
    "PatientSearchRequest",
    # Pipeline
    "PipelineCompletionUpdate",
    "PipelineProgressUpdate",
    "PipelineRunListResponse",
    "PipelineRunResponse",
    "RawVariantListResponse",
    "RawVariantResponse",
    "RefreshTokenRequest",
    "RegisterRequest",
    "ReportBytesResponse",
    "SampleListResponse",
    "SampleResponse",
    "SampleVariantListResponse",
    "SampleVariantResponse",
    "StartPipelineRequest",
    "TokenResponse",
    "UpdatePatientRequest",
    "UpdateSampleRequest",
    "UpdateUserRequest",
    "UploadFilesRequest",
    "UploadFilesResponse",
    "UserResponse",
    "VariantListResponse",
    "VariantResponse",
    "VariantSearchRequest",
]
