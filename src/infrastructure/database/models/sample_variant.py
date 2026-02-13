"""Sample variant SQLAlchemy model."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums import ACMGClassification
from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.sample import SampleModel


class SampleVariantModel(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for sample-specific variant (raw variant from pipeline)."""

    __tablename__ = "sample_variants"

    sample_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("samples.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Genomic coordinates
    chromosome: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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
    variant_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
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

    # Sequencing metrics
    depth: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    genotype: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
    )

    # Variant caller information
    variant_caller: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )
    gatk_depth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    gatk_allele_depth: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    gatk_allele_fraction: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )

    # Database lookups
    variant_db_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    variant_db_hetero_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    variant_db_homo_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    artifact_db_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Annotation (filled by geneticist)
    pop_freq_gnomad: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 8),
        nullable=True,
    )
    acmg_classification: Mapped[ACMGClassification | None] = mapped_column(
        Enum(
            ACMGClassification,
            name="acmg_classification",
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=True,
    )

    # Geneticist decision
    is_variant: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    is_artifact: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    # Relationships
    sample: Mapped["SampleModel"] = relationship(
        "SampleModel",
        back_populates="variants",
    )

    # Composite index for variant lookup within sample
    __table_args__ = (
        Index(
            "ix_sample_variant_coordinates",
            "sample_id",
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
        return f"<SampleVariant(id={self.id}, sample={self.sample_id}, name={self.variant_name})>"
