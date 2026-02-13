"""Pipeline run SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums import PipelineStatus, PipelineType
from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.sample import SampleModel


class PipelineRunModel(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for PipelineRun entity."""

    __tablename__ = "pipeline_runs"

    sample_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("samples.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_type: Mapped[PipelineType] = mapped_column(
        Enum(PipelineType, name="pipeline_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        index=True,
    )
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(
            PipelineStatus, name="pipeline_status", values_callable=lambda e: [x.value for x in e]
        ),
        nullable=False,
        default=PipelineStatus.PENDING,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    output_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    progress_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    sample: Mapped["SampleModel"] = relationship(
        "SampleModel",
        back_populates="pipeline_runs",
    )

    def __repr__(self) -> str:
        return f"<PipelineRun(id={self.id}, type={self.pipeline_type}, status={self.status})>"
