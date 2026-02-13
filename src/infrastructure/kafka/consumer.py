"""Kafka consumer service."""

import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from aiokafka import AIOKafkaConsumer

from src.config import settings
from src.infrastructure.kafka.events import TOPICS

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class KafkaConsumer:
    """Async Kafka consumer for processing events."""

    def __init__(
        self,
        topics: list[str],
        group_id: str | None = None,
    ) -> None:
        self._topics = topics
        self._group_id = group_id or settings.kafka_consumer_group
        self._consumer: AIOKafkaConsumer | None = None
        self._handlers: dict[str, EventHandler] = {}
        self._running = False

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register event handler.

        Args:
            event_type: Event type to handle
            handler: Async handler function
        """
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    async def start(self) -> None:
        """Start the Kafka consumer."""
        if self._consumer is not None:
            return

        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info(f"Kafka consumer started for topics: {self._topics}")

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
            logger.info("Kafka consumer stopped")

    async def consume(self) -> None:
        """Start consuming messages."""
        if self._consumer is None:
            raise RuntimeError("Kafka consumer is not started")

        logger.info("Starting message consumption...")

        try:
            async for message in self._consumer:
                if not self._running:
                    break

                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Consumer cancelled")
        except Exception as e:
            logger.error(f"Consumer error: {e}", exc_info=True)
            raise

    async def _process_message(self, message: Any) -> None:
        """Process a single message.

        Args:
            message: Kafka message
        """
        event_data = message.value
        event_type = event_data.get("event_type")

        logger.debug(f"Received event: {event_type} from topic {message.topic}")

        handler = self._handlers.get(event_type)
        if handler:
            await handler(event_data)
        else:
            logger.warning(f"No handler registered for event type: {event_type}")


def create_pipeline_worker_consumer() -> KafkaConsumer:
    """Create consumer for pipeline worker."""
    return KafkaConsumer(
        topics=[TOPICS["pipeline_commands"]],
        group_id=f"{settings.kafka_consumer_group}-pipeline-worker",
    )


def create_event_processor_consumer() -> KafkaConsumer:
    """Create consumer for processing pipeline events."""
    return KafkaConsumer(
        topics=[TOPICS["pipeline_events"]],
        group_id=f"{settings.kafka_consumer_group}-event-processor",
    )
