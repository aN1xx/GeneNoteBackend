"""Preview report use case."""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.report import ReportBytesResponse
from src.application.use_cases.report.utils import get_fastp_stats, get_logo_path
from src.config import settings
from src.domain.enums import SampleStatus
from src.domain.exceptions import PatientNotFoundError, SampleNotFoundError, ValidationError
from src.domain.repositories import IUnitOfWork
from src.infrastructure.report import ReportGenerator


@dataclass
class PreviewReportUseCase:
    """Use case for generating PDF report preview (without saving)."""

    uow: IUnitOfWork

    async def execute(self, sample_id: UUID) -> ReportBytesResponse:
        """Generate PDF report preview on-the-fly.

        Args:
            sample_id: Sample UUID

        Returns:
            Report bytes response

        Raises:
            SampleNotFoundError: If sample not found
            PatientNotFoundError: If patient not found
            ValidationError: If sample is not in ANNOTATED or REPORT_GENERATED status
        """
        async with self.uow:
            # Get sample
            sample = await self.uow.samples.get_by_id(sample_id)
            if not sample:
                raise SampleNotFoundError(str(sample_id))

            # Validate sample status
            if sample.status not in [SampleStatus.ANNOTATED, SampleStatus.REPORT_GENERATED]:
                raise ValidationError(
                    f"Sample must be annotated to preview report. "
                    f"Current status: {sample.status.value}"
                )

            # Get patient
            patient = await self.uow.patients.get_by_id(sample.patient_id)
            if not patient:
                raise PatientNotFoundError(str(sample.patient_id))

            # Get confirmed variants
            variants = await self.uow.sample_variants.get_confirmed_variants(sample_id)

            # Get coverage
            coverage = await self.uow.sample_coverages.get_by_sample_id(sample_id)

            # Get read statistics from fastp JSON
            read_stats = get_fastp_stats(sample.sample_code)

            # Generate report bytes
            font_path = str(settings.pdf_font_path) if settings.pdf_font_path else None
            logo_path = get_logo_path()
            generator = ReportGenerator(font_path=font_path, logo_path=logo_path)
            pdf_bytes = generator.generate_report_bytes(
                sample=sample,
                patient=patient,
                variants=variants,
                coverage=coverage,
                read_stats=read_stats,
            )

            # Preview is always for annotated results (not resequencing notice)
            # Resequencing reports are only generated via request-resequencing endpoint
            is_resequencing_report = False

            return ReportBytesResponse(
                sample_id=sample.id,
                sample_code=sample.sample_code,
                pdf_bytes=pdf_bytes,
                filename=f"{sample.sample_code}_preview.pdf",
                is_resequencing_report=is_resequencing_report,
            )
