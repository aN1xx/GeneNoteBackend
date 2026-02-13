"""Add pipeline file types to file_type enum.

Revision ID: 004
Revises: 003
Create Date: 2024-12-29

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new file types to file_type enum
    op.execute("ALTER TYPE file_type ADD VALUE IF NOT EXISTS 'bam_index'")
    op.execute("ALTER TYPE file_type ADD VALUE IF NOT EXISTS 'vcf_gatk'")
    op.execute("ALTER TYPE file_type ADD VALUE IF NOT EXISTS 'vcf_ngsep'")
    op.execute("ALTER TYPE file_type ADD VALUE IF NOT EXISTS 'vcf_xatlas'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum values in place
    # If needed, a more complex migration would be required
    pass

