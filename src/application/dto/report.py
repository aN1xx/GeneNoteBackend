"""Report DTOs for API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.enums import SampleStatus


class GenerateReportResponse(BaseModel):
    """Response for report generation."""

    sample_id: UUID
    sample_code: str
    report_path: str
    status: SampleStatus
    generated_at: datetime


class ReportBytesResponse(BaseModel):
    """Response containing report PDF bytes."""

    sample_id: UUID
    sample_code: str
    pdf_bytes: bytes
    filename: str
    is_resequencing_report: bool = Field(
        default=False,
        description="True if this is a resequencing notice report, False if it's an annotated result report",
    )
