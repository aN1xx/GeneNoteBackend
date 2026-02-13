"""User role enumeration."""

from enum import StrEnum


class UserRole(StrEnum):
    """User roles for access control."""

    LABORANT = "laborant"
    GENETICIST = "geneticist"
    ADMIN = "admin"

    def can_upload_files(self) -> bool:
        """Check if role can upload files."""
        return self in (UserRole.LABORANT, UserRole.ADMIN)

    def can_start_variant_calling(self) -> bool:
        """Check if role can start variant calling pipeline."""
        return self in (UserRole.LABORANT, UserRole.ADMIN)

    def can_annotate_variants(self) -> bool:
        """Check if role can annotate variants."""
        return self in (UserRole.GENETICIST, UserRole.ADMIN)

    def can_generate_reports(self) -> bool:
        """Check if role can start report generation."""
        return self in (UserRole.GENETICIST, UserRole.ADMIN)

    def can_manage_users(self) -> bool:
        """Check if role can manage users."""
        return self == UserRole.ADMIN
