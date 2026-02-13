"""Kafka event schemas."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from src.domain.enums import PipelineType


class EventType(StrEnum):
    """Types of Kafka events."""

    # Pipeline events
    PIPELINE_START_REQUESTED = "pipeline.start.requested"
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_PROGRESS = "pipeline.progress"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    PIPELINE_CANCELLED = "pipeline.cancelled"

    # Sample events
    SAMPLE_UPLOADED = "sample.uploaded"
    SAMPLE_PROCESSING_COMPLETE = "sample.processing.complete"
    SAMPLE_ANNOTATION_COMPLETE = "sample.annotation.complete"


class BaseEvent(BaseModel):
    """Base event schema."""

    event_type: EventType
    timestamp: datetime
    correlation_id: UUID | None = None

    class Config:
        use_enum_values = True


class PipelineStartRequestedEvent(BaseEvent):
    """Event for requesting pipeline start."""

    event_type: EventType = EventType.PIPELINE_START_REQUESTED
    pipeline_id: UUID
    sample_id: UUID
    sample_code: str
    pipeline_type: PipelineType
    fastq_r1_path: str
    fastq_r2_path: str
    output_dir: str


class PipelineStartedEvent(BaseEvent):
    """Event when pipeline execution starts."""

    event_type: EventType = EventType.PIPELINE_STARTED
    pipeline_id: UUID
    sample_id: UUID
    pipeline_type: PipelineType


class PipelineProgressEvent(BaseEvent):
    """Event for pipeline progress updates."""

    event_type: EventType = EventType.PIPELINE_PROGRESS
    pipeline_id: UUID
    progress_percent: int
    current_step: str | None = None
    message: str | None = None


class PipelineCompletedEvent(BaseEvent):
    """Event when pipeline completes successfully."""

    event_type: EventType = EventType.PIPELINE_COMPLETED
    pipeline_id: UUID
    sample_id: UUID
    pipeline_type: PipelineType
    output_path: str
    duration_seconds: int


class PipelineFailedEvent(BaseEvent):
    """Event when pipeline fails."""

    event_type: EventType = EventType.PIPELINE_FAILED
    pipeline_id: UUID
    sample_id: UUID
    pipeline_type: PipelineType
    error_message: str
    error_details: str | None = None


class PipelineCancelledEvent(BaseEvent):
    """Event when pipeline is cancelled."""

    event_type: EventType = EventType.PIPELINE_CANCELLED
    pipeline_id: UUID
    sample_id: UUID
    pipeline_type: PipelineType


class SampleUploadedEvent(BaseEvent):
    """Event when sample files are uploaded."""

    event_type: EventType = EventType.SAMPLE_UPLOADED
    sample_id: UUID
    patient_id: UUID
    sample_code: str
    fastq_r1_path: str
    fastq_r2_path: str


# Topic configuration
TOPICS = {
    "pipeline_commands": "genenote.pipeline.commands",
    "pipeline_events": "genenote.pipeline.events",
    "sample_events": "genenote.sample.events",
}
