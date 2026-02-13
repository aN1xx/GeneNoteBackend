"""User entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.enums import UserRole


@dataclass
class User:
    """Domain entity representing a system user."""

    email: str
    role: UserRole
    id: UUID = field(default_factory=uuid4)
    hashed_password: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate user data."""
        if not self.email or "@" not in self.email:
            msg = "Invalid email address"
            raise ValueError(msg)

    def can_upload_files(self) -> bool:
        """Check if user can upload files."""
        return self.is_active and self.role.can_upload_files()

    def can_start_variant_calling(self) -> bool:
        """Check if user can start variant calling pipeline."""
        return self.is_active and self.role.can_start_variant_calling()

    def can_annotate_variants(self) -> bool:
        """Check if user can annotate variants."""
        return self.is_active and self.role.can_annotate_variants()

    def can_generate_reports(self) -> bool:
        """Check if user can generate reports."""
        return self.is_active and self.role.can_generate_reports()

    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.is_active and self.role.can_manage_users()

    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def change_role(self, new_role: UserRole) -> None:
        """Change user role."""
        self.role = new_role
        self.updated_at = datetime.utcnow()
