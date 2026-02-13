"""Artifact SQLAlchemy model."""

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class ArtifactModel(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for GermlineArtifact entity."""

    __tablename__ = "germline_artifacts"

    # Genomic coordinates
    chromosome: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    ref: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    alt: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    # Statistics
    occurrence_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    sample_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Composite unique index for genomic coordinates
    __table_args__ = (
        Index(
            "ix_artifact_coordinates",
            "chromosome",
            "position",
            "ref",
            "alt",
            unique=True,
        ),
    )

    @property
    def artifact_name(self) -> str:
        """Generate artifact name in standard format."""
        return f"chr{self.chromosome}-{self.position}-{self.ref}-{self.alt}"

    def __repr__(self) -> str:
        return f"<Artifact(id={self.id}, name={self.artifact_name}, occurrences={self.occurrence_num})>"
