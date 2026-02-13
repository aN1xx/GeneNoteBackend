"""Patient-Variant association model (Many-to-Many with extra data)."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.patient import PatientModel
    from src.infrastructure.database.models.variant import VariantModel


class PatientVariantModel(Base, UUIDMixin, TimestampMixin):
    """Association model linking patients to their variants.

    This is a many-to-many relationship with additional data (zygosity).
    """

    __tablename__ = "patient_variants"

    patient_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("germline_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zygosity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="het",  # "het" (heterozygous) or "hom" (homozygous)
    )

    # Relationships
    patient: Mapped["PatientModel"] = relationship(
        "PatientModel",
        back_populates="patient_variants",
    )
    variant: Mapped["VariantModel"] = relationship(
        "VariantModel",
        back_populates="patient_variants",
    )

    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            "variant_id",
            name="uq_patient_variant",
        ),
    )

    @property
    def is_heterozygous(self) -> bool:
        """Check if zygosity is heterozygous."""
        return self.zygosity.lower() in ("het", "heterozygous", "гетерозигота")

    @property
    def is_homozygous(self) -> bool:
        """Check if zygosity is homozygous."""
        return self.zygosity.lower() in ("hom", "homozygous", "гомозигота")

    def __repr__(self) -> str:
        return f"<PatientVariant(patient={self.patient_id}, variant={self.variant_id}, zygosity={self.zygosity})>"
