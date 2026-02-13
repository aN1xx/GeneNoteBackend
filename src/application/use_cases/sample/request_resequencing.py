"""Request resequencing use case."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.application.dto.sample import SampleResponse
from src.application.use_cases.report.utils import get_logo_path
from src.config import settings
from src.domain.enums import SampleStatus
from src.domain.exceptions import PatientNotFoundError, SampleNotFoundError, ValidationError
from src.domain.repositories import IUnitOfWork
from src.infrastructure.report import ReportGenerator


def _to_response(sample) -> SampleResponse:
    """Convert sample entity to response DTO."""
    has_report = sample.report_path is not None
    is_resequencing_report = bool(sample.requires_resequencing) if has_report else None

    return SampleResponse(
        id=sample.id,
        patient_id=sample.patient_id,
        sample_code=sample.sample_code,
        status=sample.status,
        collection_date=sample.collection_date,
        fastq_r1_path=sample.fastq_r1_path,
        fastq_r2_path=sample.fastq_r2_path,
        tsv_patients_path=sample.tsv_patients_path,
        has_fastq_files=sample.has_fastq_files(),
        can_start_variant_calling=sample.can_start_variant_calling(),
        can_annotate=sample.can_annotate(),
        can_generate_report=sample.can_generate_report(),
        has_report=has_report,
        is_resequencing_report=is_resequencing_report,
        created_at=sample.created_at,
        updated_at=sample.updated_at,
    )


@dataclass
class RequestResequencingUseCase:
    """Use case for requesting resequencing for a sample."""

    uow: IUnitOfWork

    async def execute(self, sample_id: UUID, user_id: UUID) -> SampleResponse:
        """Request resequencing for a sample.

        This will:
        1. Validate sample is in AWAITING_ANNOTATION or ANNOTATED status
        2. Generate resequencing notice PDF report
        3. Set sample status to REPORT_GENERATED
        4. Mark sample as requiring resequencing

        Args:
            sample_id: Sample UUID
            user_id: User ID who requested resequencing

        Returns:
            Sample response

        Raises:
            SampleNotFoundError: If sample not found
            PatientNotFoundError: If patient not found
            ValidationError: If sample is not in valid status
        """
        async with self.uow:
            # Get sample
            sample = await self.uow.samples.get_by_id(sample_id)
            if not sample:
                raise SampleNotFoundError(str(sample_id))

            # Validate sample status
            if sample.status not in (SampleStatus.AWAITING_ANNOTATION, SampleStatus.ANNOTATED):
                raise ValidationError(
                    f"Sample must be in AWAITING_ANNOTATION or ANNOTATED status to request resequencing. "
                    f"Current status: {sample.status.value}"
                )

            # Get patient
            patient = await self.uow.patients.get_by_id(sample.patient_id)
            if not patient:
                raise PatientNotFoundError(str(sample.patient_id))

            # Generate resequencing report
            font_path = str(settings.pdf_font_path) if settings.pdf_font_path else None
            logo_path = get_logo_path()
            generator = ReportGenerator(font_path=font_path, logo_path=logo_path)

            reports_dir = settings.file_storage_path / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_filename = (
                f"{sample.sample_code}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            report_path = reports_dir / report_filename

            generator.generate_resequencing_report(
                sample=sample,
                patient=patient,
                output_path=report_path,
            )

            # Update sample status and mark as requiring resequencing
            sample.mark_report_generated()
            sample.report_path = str(report_path)
            sample.requires_resequencing = True
            sample.resequencing_requested_at = datetime.now(UTC)
            sample.resequencing_requested_by_id = user_id

            await self.uow.samples.save(sample)
            await self.uow.commit()

            return _to_response(sample)
