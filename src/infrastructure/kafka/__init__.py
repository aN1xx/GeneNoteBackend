"""Kafka infrastructure."""

from src.infrastructure.kafka.consumer import (
    KafkaConsumer,
    create_event_processor_consumer,
    create_pipeline_worker_consumer,
)
from src.infrastructure.kafka.events import (
    TOPICS,
    BaseEvent,
    EventType,
    PipelineCancelledEvent,
    PipelineCompletedEvent,
    PipelineFailedEvent,
    PipelineProgressEvent,
    PipelineStartedEvent,
    PipelineStartRequestedEvent,
    SampleUploadedEvent,
)
from src.infrastructure.kafka.handlers import EVENT_HANDLERS, register_event_handlers
from src.infrastructure.kafka.producer import (
    KafkaProducer,
    close_kafka_producer,
    get_kafka_producer,
)

__all__ = [
    # Handlers
    "EVENT_HANDLERS",
    "TOPICS",
    # Events
    "BaseEvent",
    "EventType",
    # Consumer
    "KafkaConsumer",
    # Producer
    "KafkaProducer",
    "PipelineCancelledEvent",
    "PipelineCompletedEvent",
    "PipelineFailedEvent",
    "PipelineProgressEvent",
    "PipelineStartRequestedEvent",
    "PipelineStartedEvent",
    "SampleUploadedEvent",
    "close_kafka_producer",
    "create_event_processor_consumer",
    "create_pipeline_worker_consumer",
    "get_kafka_producer",
    "register_event_handlers",
]
