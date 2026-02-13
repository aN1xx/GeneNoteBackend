"""Variant SQLAlchemy model."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums import ACMGClassification, VariantType
from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.patient_variant import PatientVariantModel


class VariantModel(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for GermlineVariant entity."""

    __tablename__ = "germline_variants"

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

    # Gene information
    gene: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    variant_type: Mapped[VariantType] = mapped_column(
        Enum(VariantType, name="variant_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=VariantType.UNKNOWN,
    )
    transcript: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
    )
    exon_intron: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    hgvs: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Population statistics
    hetero_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    homo_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    sample_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Annotation
    pop_freq_gnomad: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 8),
        nullable=True,
    )
    acmg_classification: Mapped[ACMGClassification] = mapped_column(
        Enum(
            ACMGClassification,
            name="acmg_classification",
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=False,
        default=ACMGClassification.NOT_CLASSIFIED,
        index=True,
    )

    # Changelog for ACMG classification changes
    changelog: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    # Relationships
    patient_variants: Mapped[list["PatientVariantModel"]] = relationship(
        "PatientVariantModel",
        back_populates="variant",
        lazy="selectin",
    )

    # Composite unique index for genomic coordinates
    __table_args__ = (
        Index(
            "ix_variant_coordinates",
            "chromosome",
            "position",
            "ref",
            "alt",
            unique=True,
        ),
    )

    @property
    def variant_name(self) -> str:
        """Generate variant name in standard format."""
        return f"chr{self.chromosome}-{self.position}-{self.ref}-{self.alt}"

    def __repr__(self) -> str:
        return f"<Variant(id={self.id}, name={self.variant_name}, gene={self.gene})>"
