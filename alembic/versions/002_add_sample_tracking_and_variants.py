"""Add sample tracking fields and sample_variants/coverages tables.

Revision ID: 002
Revises: 001
Create Date: 2024-12-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add tracking columns to samples table
    op.add_column(
        "samples",
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "samples",
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "samples",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "samples",
        sa.Column("annotated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "samples",
        sa.Column(
            "annotated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "samples",
        sa.Column("coverage_quality_passed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "samples",
        sa.Column("report_path", sa.Text(), nullable=True),
    )

    # Create sample_variants table
    op.create_table(
        "sample_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sample_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("samples.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Genomic coordinates
        sa.Column("chromosome", sa.String(5), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("ref", sa.String(1000), nullable=False),
        sa.Column("alt", sa.String(1000), nullable=False),
        # Gene information
        sa.Column("gene", sa.String(50), nullable=False, index=True),
        sa.Column("variant_type", sa.String(100), nullable=True),
        sa.Column("transcript", sa.String(50), nullable=False, server_default=""),
        sa.Column("exon_intron", sa.String(50), nullable=True),
        sa.Column("hgvs", sa.String(500), nullable=True),
        # Sequencing metrics
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("genotype", sa.String(50), nullable=False, server_default=""),
        # Variant caller information
        sa.Column("variant_caller", sa.String(100), nullable=False, server_default=""),
        sa.Column("gatk_depth", sa.Integer(), nullable=True),
        sa.Column("gatk_allele_depth", sa.Integer(), nullable=True),
        sa.Column("gatk_allele_fraction", sa.Numeric(10, 6), nullable=True),
        # Database lookups
        sa.Column("variant_db_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("variant_db_hetero_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("variant_db_homo_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("artifact_db_num", sa.Integer(), nullable=False, server_default="0"),
        # Annotation (filled by geneticist)
        sa.Column("pop_freq_gnomad", sa.Numeric(10, 8), nullable=True),
        sa.Column(
            "acmg_classification",
            postgresql.ENUM(name="acmg_classification", create_type=False),
            nullable=True,
        ),
        # Geneticist decision
        sa.Column("is_variant", sa.Boolean(), nullable=True),
        sa.Column("is_artifact", sa.Boolean(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create unique index for variant coordinates within sample
    op.create_index(
        "ix_sample_variant_coordinates",
        "sample_variants",
        ["sample_id", "chromosome", "position", "ref", "alt"],
        unique=True,
    )

    # Create sample_coverages table
    op.create_table(
        "sample_coverages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sample_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("samples.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        # Coverage percentages at different depths
        sa.Column("depth_0x", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("depth_5x", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("depth_30x", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("depth_50x", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("depth_100x", sa.Numeric(5, 2), nullable=False, server_default="0"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table("sample_coverages")
    op.drop_index("ix_sample_variant_coordinates", table_name="sample_variants")
    op.drop_table("sample_variants")

    # Remove columns from samples table
    op.drop_column("samples", "report_path")
    op.drop_column("samples", "coverage_quality_passed")
    op.drop_column("samples", "annotated_by_id")
    op.drop_column("samples", "annotated_at")
    op.drop_column("samples", "processed_at")
    op.drop_column("samples", "uploaded_by_id")
    op.drop_column("samples", "uploaded_at")
