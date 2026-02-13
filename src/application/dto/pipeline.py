"""Pipeline DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.enums import PipelineStatus, PipelineType


class StartPipelineRequest(BaseModel):
    """Start pipeline request DTO."""

    sample_id: UUID
    pipeline_type: PipelineType


class PipelineRunResponse(BaseModel):
    """Pipeline run response DTO."""

    id: UUID
    sample_id: UUID
    pipeline_type: PipelineType
    status: PipelineStatus
    started_at: datetime | None
    completed_at: datetime | None
    output_path: str | None
    error_message: str | None
    progress_percent: int | None
    duration_seconds: int | None
    is_terminal: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PipelineRunListResponse(BaseModel):
    """Pipeline run list response DTO."""

    items: list[PipelineRunResponse]
    total: int
    limit: int
    offset: int


class PipelineProgressUpdate(BaseModel):
    """Pipeline progress update DTO (from Kafka)."""

    pipeline_id: UUID
    progress_percent: int
    message: str | None = None


class PipelineCompletionUpdate(BaseModel):
    """Pipeline completion update DTO (from Kafka)."""

    pipeline_id: UUID
    success: bool
    output_path: str | None = None
    error_message: str | None = None
