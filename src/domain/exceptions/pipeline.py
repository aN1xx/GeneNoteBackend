"""Pipeline-related domain exceptions."""

from src.domain.exceptions.base import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)


class PipelineRunNotFoundError(EntityNotFoundError):
    """Raised when a pipeline run is not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__("PipelineRun", identifier)


class PipelineAlreadyRunningError(BusinessRuleViolationError):
    """Raised when trying to start a pipeline that is already running."""

    def __init__(self, sample_id: str, pipeline_type: str) -> None:
        self.sample_id = sample_id
        self.pipeline_type = pipeline_type
        super().__init__(
            rule="Only one pipeline of each type can run per sample",
            details=f"{pipeline_type} pipeline already running for sample {sample_id}",
        )


class PipelineNotCancellableError(BusinessRuleViolationError):
    """Raised when trying to cancel a pipeline that cannot be cancelled."""

    def __init__(self, pipeline_id: str, current_status: str) -> None:
        self.pipeline_id = pipeline_id
        super().__init__(
            rule="Pipeline can only be cancelled when pending, queued, or running",
            details=f"Pipeline {pipeline_id} is in status '{current_status}'",
        )


class PipelineExecutionError(BusinessRuleViolationError):
    """Raised when pipeline execution fails."""

    def __init__(self, pipeline_id: str, error_message: str) -> None:
        self.pipeline_id = pipeline_id
        self.error_message = error_message
        super().__init__(
            rule="Pipeline execution must complete successfully",
            details=f"Pipeline {pipeline_id} failed: {error_message}",
        )
