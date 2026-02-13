"""Pipeline status enumeration."""

from enum import StrEnum


class PipelineStatus(StrEnum):
    """Status of a pipeline run."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        """Check if status is terminal (no further transitions)."""
        return self in (
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
            PipelineStatus.CANCELLED,
        )

    def is_active(self) -> bool:
        """Check if pipeline is actively running."""
        return self in (PipelineStatus.PENDING, PipelineStatus.QUEUED, PipelineStatus.RUNNING)

    def can_cancel(self) -> bool:
        """Check if pipeline can be cancelled."""
        return self in (PipelineStatus.PENDING, PipelineStatus.QUEUED, PipelineStatus.RUNNING)


class PipelineType(StrEnum):
    """Types of pipelines."""

    VARIANT_CALLING = "variant_calling"
    REPORT_GENERATION = "report_generation"
