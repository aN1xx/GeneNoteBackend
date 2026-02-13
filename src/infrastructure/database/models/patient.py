"""Patient SQLAlchemy model."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums import Sex
from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.infrastructure.database.models.patient_variant import PatientVariantModel
    from src.infrastructure.database.models.sample import SampleModel


class SexType(TypeDecorator):
    """Custom type for Sex enum that uses values instead of names."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Use PostgreSQL ENUM for PostgreSQL, String for others."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ENUM("м", "ж", "unknown", name="sex", create_type=False))
        return dialect.type_descriptor(String(50))

    def process_bind_param(self, value, dialect):
        """Convert enum to its value for database storage."""
        if value is None:
            return None
        if isinstance(value, Sex):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        """Convert database value back to enum."""
        if value is None:
            return None
        if isinstance(value, str):
            return Sex(value)
        return value


class PatientModel(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for Patient entity."""

    __tablename__ = "patients"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    sex: Mapped[Sex] = mapped_column(
        SexType(),
        nullable=False,
    )
    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    analysis_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    analysis_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Relationships
    samples: Mapped[list["SampleModel"]] = relationship(
        "SampleModel",
        back_populates="patient",
        lazy="selectin",
    )
    patient_variants: Mapped[list["PatientVariantModel"]] = relationship(
        "PatientVariantModel",
        back_populates="patient",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, name={self.name}, request_id={self.request_id})>"
