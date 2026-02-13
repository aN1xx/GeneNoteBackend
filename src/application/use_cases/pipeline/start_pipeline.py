"""Start pipeline use case."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from src.application.dto.pipeline import PipelineRunResponse, StartPipelineRequest
from src.config import settings
from src.domain.entities import PipelineRun
from src.domain.enums import PipelineType
from src.domain.exceptions import (
    PipelineAlreadyRunningError,
    SampleNotFoundError,
    SampleNotReadyForProcessingError,
)
from src.domain.repositories import IUnitOfWork
from src.infrastructure.kafka import KafkaProducer, PipelineStartRequestedEvent


def _to_response(run: PipelineRun) -> PipelineRunResponse:
    """Convert pipeline run entity to response DTO."""
    return PipelineRunResponse(
        id=run.id,
        sample_id=run.sample_id,
        pipeline_type=run.pipeline_type,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        output_path=run.output_path,
        error_message=run.error_message,
        progress_percent=run.progress_percent,
        duration_seconds=run.duration_seconds,
        is_terminal=run.is_terminal,
        is_active=run.is_active,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@dataclass
class StartPipelineUseCase:
    """Use case for starting a pipeline."""

    uow: IUnitOfWork
    kafka_producer: KafkaProducer | None = None

    async def execute(self, request: StartPipelineRequest) -> PipelineRunResponse:
        """Execute start pipeline use case.

        Args:
            request: Start pipeline request

        Returns:
            Created pipeline run response

        Raises:
            SampleNotFoundError: If sample does not exist
            SampleNotReadyForProcessingError: If sample is not ready
            PipelineAlreadyRunningError: If pipeline is already running
        """
        async with self.uow:
            # Verify sample exists
            sample = await self.uow.samples.get_by_id(request.sample_id)
            if not sample:
                raise SampleNotFoundError(str(request.sample_id))

            # Check if sample is ready for processing
            if request.pipeline_type == PipelineType.VARIANT_CALLING:
                if not sample.can_start_variant_calling():
                    raise SampleNotReadyForProcessingError(
                        str(request.sample_id),
                        "Sample is not ready for variant calling",
                    )
            elif request.pipeline_type == PipelineType.REPORT_GENERATION:
                if not sample.can_generate_report():
                    raise SampleNotReadyForProcessingError(
                        str(request.sample_id),
                        "Sample is not ready for report generation",
                    )

            # Check for existing active runs
            if await self.uow.pipelines.has_active_run(request.sample_id, request.pipeline_type):
                raise PipelineAlreadyRunningError(
                    str(request.sample_id), request.pipeline_type.value
                )

            # Create pipeline run
            pipeline_id = uuid4()
            pipeline_run = PipelineRun(
                id=pipeline_id,
                sample_id=request.sample_id,
                pipeline_type=request.pipeline_type,
            )

            # Mark as queued
            pipeline_run.queue()

            saved_run = await self.uow.pipelines.save(pipeline_run)

            # Update sample status
            if request.pipeline_type == PipelineType.VARIANT_CALLING:
                sample.mark_processing()
                await self.uow.samples.save(sample)

            await self.uow.commit()

            # Send Kafka event to start pipeline
            if self.kafka_producer and sample.fastq_r1_path and sample.fastq_r2_path:
                output_dir = str(settings.file_storage_path / sample.sample_code / "output")
                event = PipelineStartRequestedEvent(
                    timestamp=datetime.now(UTC),
                    correlation_id=pipeline_id,
                    pipeline_id=pipeline_id,
                    sample_id=sample.id,
                    sample_code=sample.sample_code,
                    pipeline_type=request.pipeline_type,
                    fastq_r1_path=sample.fastq_r1_path,
                    fastq_r2_path=sample.fastq_r2_path,
                    output_dir=output_dir,
                )
                await self.kafka_producer.send_pipeline_command(event)

            return _to_response(saved_run)
