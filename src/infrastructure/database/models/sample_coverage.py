"""Sample coverage SQLAlchemy model."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.sample import SampleModel


class SampleCoverageModel(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for sample coverage statistics."""

    __tablename__ = "sample_coverages"

    sample_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("samples.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One coverage record per sample
        index=True,
    )

    # Coverage percentages at different depths
    depth_0x: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
    )
    depth_5x: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
    )
    depth_30x: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
    )
    depth_50x: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
    )
    depth_100x: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0"),
    )

    # Relationships
    sample: Mapped["SampleModel"] = relationship(
        "SampleModel",
        backref="coverage",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<SampleCoverage(sample={self.sample_id}, 30x={self.depth_30x}%)>"
