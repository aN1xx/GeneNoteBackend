"""Pipeline run entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.enums import PipelineStatus, PipelineType


@dataclass
class PipelineRun:
    """Domain entity representing a pipeline execution run."""

    sample_id: UUID
    pipeline_type: PipelineType
    id: UUID = field(default_factory=uuid4)
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_path: str | None = None
    error_message: str | None = None
    progress_percent: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def start(self) -> None:
        """Mark pipeline as started."""
        if not self.status.can_cancel():
            msg = f"Cannot start pipeline in status {self.status}"
            raise ValueError(msg)
        self.status = PipelineStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def complete(self, output_path: str) -> None:
        """Mark pipeline as completed successfully."""
        if self.status != PipelineStatus.RUNNING:
            msg = f"Cannot complete pipeline in status {self.status}"
            raise ValueError(msg)
        self.status = PipelineStatus.COMPLETED
        self.output_path = output_path
        self.completed_at = datetime.utcnow()
        self.progress_percent = 100
        self.updated_at = datetime.utcnow()

    def fail(self, error_message: str) -> None:
        """Mark pipeline as failed."""
        self.status = PipelineStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel pipeline execution."""
        if not self.status.can_cancel():
            msg = f"Cannot cancel pipeline in status {self.status}"
            raise ValueError(msg)
        self.status = PipelineStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_progress(self, percent: int, message: str | None = None) -> None:
        """Update pipeline progress."""
        if self.status != PipelineStatus.RUNNING:
            msg = f"Cannot update progress for pipeline in status {self.status}"
            raise ValueError(msg)
        self.progress_percent = min(max(percent, 0), 100)
        if message:
            self.error_message = message  # Using for status messages too
        self.updated_at = datetime.utcnow()

    def queue(self) -> None:
        """Mark pipeline as queued."""
        if self.status != PipelineStatus.PENDING:
            msg = f"Cannot queue pipeline in status {self.status}"
            raise ValueError(msg)
        self.status = PipelineStatus.QUEUED
        self.updated_at = datetime.utcnow()

    @property
    def duration_seconds(self) -> int | None:
        """Calculate pipeline duration in seconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return int((end_time - self.started_at).total_seconds())

    @property
    def is_terminal(self) -> bool:
        """Check if pipeline is in terminal state."""
        return self.status.is_terminal()

    @property
    def is_active(self) -> bool:
        """Check if pipeline is actively running."""
        return self.status.is_active()
