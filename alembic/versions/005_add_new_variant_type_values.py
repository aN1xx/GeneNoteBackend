"""Add new variant_type enum values.

Revision ID: 005
Revises: 004
Create Date: 2025-01-13

This migration only adds new enum values.
Data migration happens in 006.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new enum values
    # These must be committed before they can be used in UPDATE statements
    op.execute("ALTER TYPE variant_type ADD VALUE IF NOT EXISTS 'inframe deletion'")
    op.execute("ALTER TYPE variant_type ADD VALUE IF NOT EXISTS 'inframe insertion'")
    op.execute("ALTER TYPE variant_type ADD VALUE IF NOT EXISTS 'intronic SNV'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # This would require recreating the enum type, which is complex
    pass
