"""Migrate nonframeshift to inframe variant types.

Revision ID: 006
Revises: 005
Create Date: 2025-01-13

Updates existing data to use new enum values.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Commit enum changes from migration 005 before using new values
    # PostgreSQL requires COMMIT after ALTER TYPE ADD VALUE
    op.execute("COMMIT")

    # Update existing data in sample_variants table
    op.execute("""
        UPDATE sample_variants
        SET variant_type = 'inframe deletion'
        WHERE variant_type = 'nonframeshift deletion'
    """)
    op.execute("""
        UPDATE sample_variants
        SET variant_type = 'inframe insertion'
        WHERE variant_type = 'nonframeshift insertion'
    """)

    # Update existing data in germline_variants table
    op.execute("""
        UPDATE germline_variants
        SET variant_type = 'inframe deletion'
        WHERE variant_type = 'nonframeshift deletion'
    """)
    op.execute("""
        UPDATE germline_variants
        SET variant_type = 'inframe insertion'
        WHERE variant_type = 'nonframeshift insertion'
    """)


def downgrade() -> None:
    # Revert data changes
    op.execute("""
        UPDATE sample_variants
        SET variant_type = 'nonframeshift deletion'
        WHERE variant_type = 'inframe deletion'
    """)
    op.execute("""
        UPDATE sample_variants
        SET variant_type = 'nonframeshift insertion'
        WHERE variant_type = 'inframe insertion'
    """)

    op.execute("""
        UPDATE germline_variants
        SET variant_type = 'nonframeshift deletion'
        WHERE variant_type = 'inframe deletion'
    """)
    op.execute("""
        UPDATE germline_variants
        SET variant_type = 'nonframeshift insertion'
        WHERE variant_type = 'inframe insertion'
    """)
