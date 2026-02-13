"""Generate report use case."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.application.dto.report import GenerateReportResponse
from src.application.use_cases.report.utils import get_fastp_stats, get_logo_path
from src.config import settings
from src.domain.enums import SampleStatus
from src.domain.exceptions import PatientNotFoundError, SampleNotFoundError, ValidationError
from src.domain.repositories import IUnitOfWork
from src.infrastructure.report import ReportGenerator


@dataclass
class GenerateReportUseCase:
    """Use case for generating and saving PDF report for a sample."""

    uow: IUnitOfWork

    async def execute(self, sample_id: UUID) -> GenerateReportResponse:
        """Generate and save PDF report.

        Args:
            sample_id: Sample UUID

        Returns:
            Report generation response

        Raises:
            SampleNotFoundError: If sample not found
            PatientNotFoundError: If patient not found
            ValidationError: If sample is not in ANNOTATED status
        """
        async with self.uow:
            # Get sample
            sample = await self.uow.samples.get_by_id(sample_id)
            if not sample:
                raise SampleNotFoundError(str(sample_id))

            # Validate sample status
            if sample.status != SampleStatus.ANNOTATED:
                raise ValidationError(
                    f"Sample must be annotated before report generation. "
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

            # Generate report
            font_path = str(settings.pdf_font_path) if settings.pdf_font_path else None
            logo_path = get_logo_path()
            generator = ReportGenerator(font_path=font_path, logo_path=logo_path)

            reports_dir = settings.file_storage_path / "reports"
            report_filename = (
                f"{sample.sample_code}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            report_path = reports_dir / report_filename

            generator.generate_report(
                sample=sample,
                patient=patient,
                variants=variants,
                coverage=coverage,
                output_path=report_path,
                read_stats=read_stats,
            )

            # Update sample status
            sample.status = SampleStatus.REPORT_GENERATED
            sample.report_path = str(report_path)
            await self.uow.samples.save(sample)
            await self.uow.commit()

            return GenerateReportResponse(
                sample_id=sample.id,
                sample_code=sample.sample_code,
                report_path=str(report_path),
                status=sample.status,
                generated_at=datetime.now(UTC),
            )
