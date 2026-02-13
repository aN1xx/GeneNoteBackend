"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2024-12-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create ENUM types
    user_role = postgresql.ENUM(
        "laborant", "geneticist", "admin",
        name="user_role",
        create_type=False,
    )
    user_role.create(op.get_bind(), checkfirst=True)

    sex = postgresql.ENUM(
        "м", "ж", "unknown",
        name="sex",
        create_type=False,
    )
    sex.create(op.get_bind(), checkfirst=True)

    sample_status = postgresql.ENUM(
        "uploaded", "processing", "awaiting_annotation",
        "annotated", "report_generated", "failed",
        name="sample_status",
        create_type=False,
    )
    sample_status.create(op.get_bind(), checkfirst=True)

    variant_type = postgresql.ENUM(
        "SNV", "nonsynonymous SNV", "synonymous SNV", "stopgain", "stoploss",
        "5'UTR SNV", "3'UTR SNV", "frameshift insertion", "frameshift deletion",
        "nonframeshift insertion", "nonframeshift deletion", "splicing", "unknown",
        name="variant_type",
        create_type=False,
    )
    variant_type.create(op.get_bind(), checkfirst=True)

    acmg_classification = postgresql.ENUM(
        "Патогенный", "Вероятно патогенный", "Вариант неясного значения",
        "Вероятно доброкачественный", "Доброкачественный", "Не классифицирован",
        name="acmg_classification",
        create_type=False,
    )
    acmg_classification.create(op.get_bind(), checkfirst=True)

    pipeline_type = postgresql.ENUM(
        "variant_calling", "report_generation",
        name="pipeline_type",
        create_type=False,
    )
    pipeline_type.create(op.get_bind(), checkfirst=True)

    pipeline_status = postgresql.ENUM(
        "pending", "queued", "running", "completed", "failed", "cancelled",
        name="pipeline_status",
        create_type=False,
    )
    pipeline_status.create(op.get_bind(), checkfirst=True)

    file_type = postgresql.ENUM(
        "tsv_patients", "fastq_r1", "fastq_r2", "bam", "vcf",
        "tsv_raw_variants", "tsv_depth_coverage", "tsv_annotated_variants",
        "pdf_report", "json_trim_stats",
        name="file_type",
        create_type=False,
    )
    file_type.create(op.get_bind(), checkfirst=True)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(name="user_role", create_type=False),
            nullable=False,
            server_default="laborant",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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

    # Create patients table
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column(
            "sex",
            postgresql.ENUM(name="sex", create_type=False),
            nullable=False,
        ),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("request_id", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("analysis_name", sa.Text(), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=True),
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

    # Create samples table
    op.create_table(
        "samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sample_code", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="sample_status", create_type=False),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("collection_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fastq_r1_path", sa.Text(), nullable=True),
        sa.Column("fastq_r2_path", sa.Text(), nullable=True),
        sa.Column("tsv_patients_path", sa.Text(), nullable=True),
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

    # Create germline_variants table
    op.create_table(
        "germline_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chromosome", sa.String(5), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False, index=True),
        sa.Column("ref", sa.String(1000), nullable=False),
        sa.Column("alt", sa.String(1000), nullable=False),
        sa.Column("gene", sa.String(50), nullable=False, index=True),
        sa.Column(
            "variant_type",
            postgresql.ENUM(name="variant_type", create_type=False),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("transcript", sa.String(50), nullable=False, server_default=""),
        sa.Column("exon_intron", sa.String(50), nullable=True),
        sa.Column("hgvs", sa.String(500), nullable=True),
        sa.Column("hetero_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("homo_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pop_freq_gnomad", sa.Numeric(10, 8), nullable=True),
        sa.Column(
            "acmg_classification",
            postgresql.ENUM(name="acmg_classification", create_type=False),
            nullable=False,
            server_default="Не классифицирован",
            index=True,
        ),
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

    # Create unique index for variant coordinates
    op.create_index(
        "ix_variant_coordinates",
        "germline_variants",
        ["chromosome", "position", "ref", "alt"],
        unique=True,
    )

    # Create patient_variants table (many-to-many)
    op.create_table(
        "patient_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "variant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("germline_variants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("zygosity", sa.String(20), nullable=False, server_default="het"),
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
        sa.UniqueConstraint("patient_id", "variant_id", name="uq_patient_variant"),
    )

    # Create germline_artifacts table
    op.create_table(
        "germline_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chromosome", sa.String(5), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False, index=True),
        sa.Column("ref", sa.String(1000), nullable=False),
        sa.Column("alt", sa.String(1000), nullable=False),
        sa.Column("occurrence_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_num", sa.Integer(), nullable=False, server_default="0"),
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

    # Create unique index for artifact coordinates
    op.create_index(
        "ix_artifact_coordinates",
        "germline_artifacts",
        ["chromosome", "position", "ref", "alt"],
        unique=True,
    )

    # Create pipeline_runs table
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sample_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("samples.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "pipeline_type",
            postgresql.ENUM(name="pipeline_type", create_type=False),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="pipeline_status", create_type=False),
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=True),
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

    # Create file_records table
    op.create_table(
        "file_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sample_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("samples.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "file_type",
            postgresql.ENUM(name="file_type", create_type=False),
            nullable=False,
            index=True,
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("checksum_md5", sa.String(32), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("file_records")
    op.drop_table("pipeline_runs")
    op.drop_index("ix_artifact_coordinates", table_name="germline_artifacts")
    op.drop_table("germline_artifacts")
    op.drop_table("patient_variants")
    op.drop_index("ix_variant_coordinates", table_name="germline_variants")
    op.drop_table("germline_variants")
    op.drop_table("samples")
    op.drop_table("patients")
    op.drop_table("users")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS file_type")
    op.execute("DROP TYPE IF EXISTS pipeline_status")
    op.execute("DROP TYPE IF EXISTS pipeline_type")
    op.execute("DROP TYPE IF EXISTS acmg_classification")
    op.execute("DROP TYPE IF EXISTS variant_type")
    op.execute("DROP TYPE IF EXISTS sample_status")
    op.execute("DROP TYPE IF EXISTS sex")
    op.execute("DROP TYPE IF EXISTS user_role")
