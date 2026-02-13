"""Add resequencing request fields to samples table.

Revision ID: 003
Revises: 002
Create Date: 2024-12-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add resequencing request columns to samples table
    op.add_column(
        "samples",
        sa.Column("requires_resequencing", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "samples",
        sa.Column("resequencing_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "samples",
        sa.Column(
            "resequencing_requested_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Remove resequencing request columns from samples table
    op.drop_column("samples", "resequencing_requested_by_id")
    op.drop_column("samples", "resequencing_requested_at")
    op.drop_column("samples", "requires_resequencing")

