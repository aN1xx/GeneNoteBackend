"""Add fastp file types to file_type enum.

Revision ID: 008
Revises: 007
Create Date: 2025-01-14

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new file types for fastp output files
    op.execute("ALTER TYPE file_type ADD VALUE IF NOT EXISTS 'json_trim_stats'")
    op.execute("ALTER TYPE file_type ADD VALUE IF NOT EXISTS 'html_fastp_report'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    pass
