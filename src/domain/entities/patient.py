"""Patient entity."""

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from src.domain.enums import Sex


@dataclass
class Patient:
    """Domain entity representing a patient."""

    name: str
    sex: Sex
    birth_date: date
    request_id: str
    analysis_name: str
    id: UUID = field(default_factory=uuid4)
    analysis_date: date | None = None
    variant_ids: list[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate patient data."""
        if not self.name or not self.name.strip():
            msg = "Patient name cannot be empty"
            raise ValueError(msg)
        if not self.request_id or not self.request_id.strip():
            msg = "Request ID cannot be empty"
            raise ValueError(msg)

    @property
    def age(self) -> int | None:
        """Calculate patient age in years."""
        if not self.birth_date:
            return None
        today = date.today()
        years = today.year - self.birth_date.year
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years

    @property
    def first_name(self) -> str:
        """Extract first name from full name."""
        parts = self.name.split()
        return parts[1] if len(parts) > 1 else parts[0]

    @property
    def last_name(self) -> str:
        """Extract last name (surname) from full name."""
        parts = self.name.split()
        return parts[0] if parts else ""

    @property
    def patronymic(self) -> str | None:
        """Extract patronymic from full name if present."""
        parts = self.name.split()
        return parts[2] if len(parts) > 2 else None

    def add_variant(self, variant_id: UUID) -> None:
        """Add variant to patient's variant list."""
        if variant_id not in self.variant_ids:
            self.variant_ids.append(variant_id)
            self.updated_at = datetime.utcnow()

    def remove_variant(self, variant_id: UUID) -> None:
        """Remove variant from patient's variant list."""
        if variant_id in self.variant_ids:
            self.variant_ids.remove(variant_id)
            self.updated_at = datetime.utcnow()

    def set_analysis_date(self, analysis_date: date) -> None:
        """Set analysis completion date."""
        self.analysis_date = analysis_date
        self.updated_at = datetime.utcnow()

    def format_birth_date(self) -> str:
        """Format birth date as dd.mm.yyyy."""
        return self.birth_date.strftime("%d.%m.%Y")
