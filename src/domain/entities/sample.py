"""Sample entity."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.enums import SampleStatus


@dataclass
class Sample:
    """Domain entity representing a biological sample."""

    patient_id: UUID
    sample_code: str
    id: UUID = field(default_factory=uuid4)
    status: SampleStatus = SampleStatus.UPLOADED
    collection_date: datetime | None = None
    fastq_r1_path: str | None = None
    fastq_r2_path: str | None = None
    tsv_patients_path: str | None = None
    report_path: str | None = None

    # Tracking fields
    uploaded_at: datetime | None = None
    uploaded_by_id: UUID | None = None
    processed_at: datetime | None = None  # When variant calling completed
    annotated_at: datetime | None = None
    annotated_by_id: UUID | None = None

    # Geneticist decision on coverage quality
    coverage_quality_passed: bool | None = None

    # Resequencing request
    requires_resequencing: bool | None = None
    resequencing_requested_at: datetime | None = None
    resequencing_requested_by_id: UUID | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate sample data."""
        if not self.sample_code or not self.sample_code.strip():
            msg = "Sample code cannot be empty"
            raise ValueError(msg)

    def set_fastq_paths(self, r1_path: str, r2_path: str) -> None:
        """Set FASTQ file paths."""
        self.fastq_r1_path = r1_path
        self.fastq_r2_path = r2_path
        self.updated_at = datetime.utcnow()

    def has_fastq_files(self) -> bool:
        """Check if FASTQ files are uploaded."""
        return bool(self.fastq_r1_path and self.fastq_r2_path)

    def mark_processing(self) -> None:
        """Mark sample as processing."""
        self.status = SampleStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def mark_awaiting_annotation(self) -> None:
        """Mark sample as awaiting annotation."""
        self.status = SampleStatus.AWAITING_ANNOTATION
        self.updated_at = datetime.utcnow()

    def mark_annotated(self) -> None:
        """Mark sample as annotated."""
        self.status = SampleStatus.ANNOTATED
        self.updated_at = datetime.utcnow()

    def mark_report_generated(self) -> None:
        """Mark sample as having report generated."""
        self.status = SampleStatus.REPORT_GENERATED
        self.updated_at = datetime.utcnow()

    def mark_failed(self) -> None:
        """Mark sample as failed."""
        self.status = SampleStatus.FAILED
        self.updated_at = datetime.utcnow()

    def can_start_variant_calling(self) -> bool:
        """Check if variant calling can be started."""
        return self.status == SampleStatus.UPLOADED and self.has_fastq_files()

    def can_annotate(self) -> bool:
        """Check if sample can be annotated."""
        return self.status == SampleStatus.AWAITING_ANNOTATION

    def can_generate_report(self) -> bool:
        """Check if report can be generated."""
        return self.status == SampleStatus.ANNOTATED
