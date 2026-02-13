"""Kafka event handlers."""

import logging
from typing import Any
from uuid import UUID

from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.infrastructure.kafka.events import EventType

logger = logging.getLogger(__name__)


def get_uow() -> SQLAlchemyUnitOfWork:
    """Get Unit of Work instance."""
    return SQLAlchemyUnitOfWork(async_session_factory)


async def handle_pipeline_started(event_data: dict[str, Any]) -> None:
    """Handle pipeline started event.

    Updates pipeline run status in database.
    """
    pipeline_id = UUID(event_data["pipeline_id"])
    logger.info(f"Handling pipeline started: {pipeline_id}")

    uow = get_uow()
    async with uow:
        run = await uow.pipelines.get_by_id(pipeline_id)
        if run:
            run.start()
            await uow.pipelines.save(run)
            await uow.commit()
            logger.info(f"Pipeline {pipeline_id} marked as started")
        else:
            logger.warning(f"Pipeline run not found: {pipeline_id}")


async def handle_pipeline_progress(event_data: dict[str, Any]) -> None:
    """Handle pipeline progress event.

    Updates pipeline progress in database.
    """
    pipeline_id = UUID(event_data["pipeline_id"])
    progress = event_data["progress_percent"]
    message = event_data.get("message")

    logger.debug(f"Pipeline {pipeline_id} progress: {progress}%")

    uow = get_uow()
    async with uow:
        run = await uow.pipelines.get_by_id(pipeline_id)
        if run and run.is_active:
            run.update_progress(progress, message)
            await uow.pipelines.save(run)
            await uow.commit()


async def handle_pipeline_completed(event_data: dict[str, Any]) -> None:
    """Handle pipeline completed event.

    Updates pipeline and sample status in database.
    """
    pipeline_id = UUID(event_data["pipeline_id"])
    sample_id = UUID(event_data["sample_id"])
    output_path = event_data["output_path"]

    logger.info(f"Handling pipeline completed: {pipeline_id}")

    uow = get_uow()
    async with uow:
        # Update pipeline run
        run = await uow.pipelines.get_by_id(pipeline_id)
        if run:
            run.complete(output_path)
            await uow.pipelines.save(run)

            # Update sample status based on pipeline type
            sample = await uow.samples.get_by_id(sample_id)
            if sample:
                from src.domain.enums import PipelineType

                if run.pipeline_type == PipelineType.VARIANT_CALLING:
                    sample.mark_awaiting_annotation()
                elif run.pipeline_type == PipelineType.REPORT_GENERATION:
                    sample.mark_report_generated()

                await uow.samples.save(sample)

            await uow.commit()
            logger.info(f"Pipeline {pipeline_id} marked as completed")
        else:
            logger.warning(f"Pipeline run not found: {pipeline_id}")


async def handle_pipeline_failed(event_data: dict[str, Any]) -> None:
    """Handle pipeline failed event.

    Updates pipeline and sample status in database.
    """
    pipeline_id = UUID(event_data["pipeline_id"])
    sample_id = UUID(event_data["sample_id"])
    error_message = event_data["error_message"]

    logger.error(f"Pipeline {pipeline_id} failed: {error_message}")

    uow = get_uow()
    async with uow:
        # Update pipeline run
        run = await uow.pipelines.get_by_id(pipeline_id)
        if run:
            run.fail(error_message)
            await uow.pipelines.save(run)

            # Update sample status
            sample = await uow.samples.get_by_id(sample_id)
            if sample:
                sample.mark_failed()
                await uow.samples.save(sample)

            await uow.commit()
            logger.info(f"Pipeline {pipeline_id} marked as failed")


async def handle_pipeline_cancelled(event_data: dict[str, Any]) -> None:
    """Handle pipeline cancelled event."""
    pipeline_id = UUID(event_data["pipeline_id"])
    logger.info(f"Handling pipeline cancelled: {pipeline_id}")

    uow = get_uow()
    async with uow:
        run = await uow.pipelines.get_by_id(pipeline_id)
        if run and not run.is_terminal:
            run.cancel()
            await uow.pipelines.save(run)
            await uow.commit()
            logger.info(f"Pipeline {pipeline_id} marked as cancelled")


# Event handler registry
EVENT_HANDLERS = {
    EventType.PIPELINE_STARTED: handle_pipeline_started,
    EventType.PIPELINE_PROGRESS: handle_pipeline_progress,
    EventType.PIPELINE_COMPLETED: handle_pipeline_completed,
    EventType.PIPELINE_FAILED: handle_pipeline_failed,
    EventType.PIPELINE_CANCELLED: handle_pipeline_cancelled,
}


def register_event_handlers(consumer) -> None:
    """Register all event handlers with consumer.

    Args:
        consumer: KafkaConsumer instance
    """
    for event_type, handler in EVENT_HANDLERS.items():
        consumer.register_handler(event_type.value, handler)
