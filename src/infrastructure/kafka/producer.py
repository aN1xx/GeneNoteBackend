"""Kafka producer service."""

import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer

from src.config import settings
from src.infrastructure.kafka.events import TOPICS, BaseEvent

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Async Kafka producer for sending events."""

    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None
        self._bootstrap_servers = settings.kafka_bootstrap_servers

    async def start(self) -> None:
        """Start the Kafka producer."""
        if self._producer is not None:
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=self._serialize,
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")

    def _serialize(self, value: Any) -> bytes:
        """Serialize event to JSON bytes."""
        if isinstance(value, BaseEvent):
            return value.model_dump_json().encode("utf-8")
        return json.dumps(value, default=str).encode("utf-8")

    async def send_event(
        self,
        topic: str,
        event: BaseEvent,
        key: str | None = None,
    ) -> None:
        """Send event to Kafka topic.

        Args:
            topic: Kafka topic name
            event: Event to send
            key: Optional partition key
        """
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")

        try:
            await self._producer.send_and_wait(
                topic=topic,
                value=event,
                key=key,
            )
            logger.debug(f"Sent event {event.event_type} to topic {topic}")
        except Exception as e:
            logger.error(f"Failed to send event to Kafka: {e}")
            raise

    async def send_pipeline_command(self, event: BaseEvent) -> None:
        """Send pipeline command event.

        Args:
            event: Pipeline command event
        """
        await self.send_event(
            topic=TOPICS["pipeline_commands"],
            event=event,
            key=str(getattr(event, "pipeline_id", None)),
        )

    async def send_pipeline_event(self, event: BaseEvent) -> None:
        """Send pipeline status event.

        Args:
            event: Pipeline status event
        """
        await self.send_event(
            topic=TOPICS["pipeline_events"],
            event=event,
            key=str(getattr(event, "pipeline_id", None)),
        )

    async def send_sample_event(self, event: BaseEvent) -> None:
        """Send sample event.

        Args:
            event: Sample event
        """
        await self.send_event(
            topic=TOPICS["sample_events"],
            event=event,
            key=str(getattr(event, "sample_id", None)),
        )


# Global producer instance
_producer: KafkaProducer | None = None


async def get_kafka_producer() -> KafkaProducer:
    """Get or create global Kafka producer instance."""
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
        await _producer.start()
    return _producer


async def close_kafka_producer() -> None:
    """Close global Kafka producer."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
