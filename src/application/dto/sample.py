"""Sample DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.enums import SampleStatus


class CreateSampleRequest(BaseModel):
    """Create sample request DTO."""

    patient_id: UUID
    sample_code: str = Field(min_length=1, max_length=100)
    collection_date: datetime | None = None


class UpdateSampleRequest(BaseModel):
    """Update sample request DTO."""

    collection_date: datetime | None = None
    status: SampleStatus | None = None


class SampleResponse(BaseModel):
    """Sample response DTO."""

    id: UUID
    patient_id: UUID
    sample_code: str
    status: SampleStatus
    collection_date: datetime | None
    fastq_r1_path: str | None
    fastq_r2_path: str | None
    tsv_patients_path: str | None
    has_fastq_files: bool
    can_start_variant_calling: bool
    can_annotate: bool
    can_generate_report: bool
    has_report: bool = Field(description="Whether sample has a generated PDF report")
    is_resequencing_report: bool | None = Field(
        default=None,
        description="True if report is resequencing notice, False if annotated result, None if no report",
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SampleListResponse(BaseModel):
    """Sample list response DTO with pagination."""

    items: list[SampleResponse]
    total: int
    limit: int
    offset: int


class UploadFilesRequest(BaseModel):
    """Upload files request DTO (metadata only, files via multipart)."""

    sample_id: UUID


class UploadFilesResponse(BaseModel):
    """Upload files response DTO."""

    sample_id: UUID
    fastq_r1_path: str
    fastq_r2_path: str
    tsv_patients_path: str | None
    status: SampleStatus


class SampleCoverageResponse(BaseModel):
    """Sample coverage response DTO."""

    sample_id: UUID
    has_coverage: bool = Field(description="Whether coverage data exists for this sample")
    depth_0x: float = Field(description="Percentage covered at >0x depth")
    depth_5x: float = Field(description="Percentage covered at >5x depth")
    depth_30x: float = Field(description="Percentage covered at >30x depth")
    depth_50x: float = Field(description="Percentage covered at >50x depth")
    depth_100x: float = Field(description="Percentage covered at >100x depth")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
