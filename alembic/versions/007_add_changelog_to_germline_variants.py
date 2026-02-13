"""Add changelog column to germline_variants table.

Revision ID: 007
Revises: 006
Create Date: 2025-01-13

Adds changelog column for tracking ACMG classification changes.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "germline_variants",
        sa.Column("changelog", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("germline_variants", "changelog")
