"""Kafka worker entry point."""

import argparse
import asyncio
import contextlib
import logging
import signal
import sys

from src.infrastructure.kafka import (
    EventType,
    close_kafka_producer,
    get_kafka_producer,
)
from src.infrastructure.kafka.consumer import (
    create_event_processor_consumer,
    create_pipeline_worker_consumer,
)
from src.infrastructure.kafka.handlers import register_event_handlers
from src.infrastructure.pipeline import PipelineWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_event_processor() -> None:
    """Run the event processor worker (updates DB based on pipeline events)."""
    consumer = create_event_processor_consumer()
    register_event_handlers(consumer)

    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await consumer.start()
        logger.info("Event processor started...")

        consume_task = asyncio.create_task(consumer.consume())
        await stop_event.wait()

        consume_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await consume_task

    finally:
        await consumer.stop()
        logger.info("Event processor stopped")


async def run_pipeline_worker() -> None:
    """Run the pipeline worker (executes Snakemake pipelines)."""
    # Initialize Kafka producer for sending events
    kafka_producer = await get_kafka_producer()
    pipeline_worker = PipelineWorker(kafka_producer)

    # Create consumer for pipeline commands
    consumer = create_pipeline_worker_consumer()
    consumer.register_handler(
        EventType.PIPELINE_START_REQUESTED.value,
        pipeline_worker.handle_pipeline_start,
    )

    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await consumer.start()
        logger.info("Pipeline worker started...")

        consume_task = asyncio.create_task(consumer.consume())
        await stop_event.wait()

        consume_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await consume_task

    finally:
        await consumer.stop()
        await close_kafka_producer()
        logger.info("Pipeline worker stopped")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="GeneNote Worker")
    parser.add_argument(
        "--mode",
        choices=["event-processor", "pipeline"],
        default="event-processor",
        help="Worker mode: event-processor (DB updates) or pipeline (Snakemake execution)",
    )
    args = parser.parse_args()

    logger.info(f"Starting GeneNote worker in {args.mode} mode...")

    try:
        if args.mode == "pipeline":
            asyncio.run(run_pipeline_worker())
        else:
            asyncio.run(run_event_processor())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
