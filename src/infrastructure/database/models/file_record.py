"""File record SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums import FileType
from src.infrastructure.database.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.sample import SampleModel


class FileRecordModel(Base, UUIDMixin):
    """SQLAlchemy model for FileRecord entity."""

    __tablename__ = "file_records"

    sample_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("samples.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, name="file_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )
    checksum_md5: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    sample: Mapped["SampleModel"] = relationship(
        "SampleModel",
        back_populates="files",
    )

    def __repr__(self) -> str:
        return f"<FileRecord(id={self.id}, name={self.file_name}, type={self.file_type})>"
