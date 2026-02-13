"""Sample SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums import SampleStatus
from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.file_record import FileRecordModel
    from src.infrastructure.database.models.patient import PatientModel
    from src.infrastructure.database.models.pipeline_run import PipelineRunModel
    from src.infrastructure.database.models.sample_variant import SampleVariantModel
    from src.infrastructure.database.models.user import UserModel


class SampleStatusType(TypeDecorator):
    """Custom type for SampleStatus enum that uses values instead of names."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Use PostgreSQL ENUM for PostgreSQL, String for others."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(
                ENUM(
                    "uploaded",
                    "processing",
                    "awaiting_annotation",
                    "annotated",
                    "report_generated",
                    "failed",
                    name="sample_status",
                    create_type=False,
                )
            )
        return dialect.type_descriptor(String(50))

    def process_bind_param(self, value, dialect):
        """Convert enum to its value for database storage."""
        if value is None:
            return None
        if isinstance(value, SampleStatus):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        """Convert database value back to enum."""
        if value is None:
            return None
        if isinstance(value, str):
            return SampleStatus(value)
        return value


class SampleModel(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for Sample entity."""

    __tablename__ = "samples"

    patient_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sample_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[SampleStatus] = mapped_column(
        SampleStatusType(),
        nullable=False,
        default=SampleStatus.UPLOADED,
    )
    collection_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    fastq_r1_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    fastq_r2_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    tsv_patients_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    report_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Tracking fields
    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    uploaded_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    annotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    annotated_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Geneticist decision on coverage quality
    coverage_quality_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    # Resequencing request
    requires_resequencing: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    resequencing_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resequencing_requested_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    patient: Mapped["PatientModel"] = relationship(
        "PatientModel",
        back_populates="samples",
    )
    uploaded_by: Mapped["UserModel | None"] = relationship(
        "UserModel",
        foreign_keys=[uploaded_by_id],
    )
    annotated_by: Mapped["UserModel | None"] = relationship(
        "UserModel",
        foreign_keys=[annotated_by_id],
    )
    files: Mapped[list["FileRecordModel"]] = relationship(
        "FileRecordModel",
        back_populates="sample",
        lazy="selectin",
    )
    pipeline_runs: Mapped[list["PipelineRunModel"]] = relationship(
        "PipelineRunModel",
        back_populates="sample",
        lazy="selectin",
    )
    variants: Mapped[list["SampleVariantModel"]] = relationship(
        "SampleVariantModel",
        back_populates="sample",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Sample(id={self.id}, code={self.sample_code}, status={self.status})>"
