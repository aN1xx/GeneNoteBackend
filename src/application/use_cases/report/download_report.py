"""Download report use case."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from src.application.dto.report import ReportBytesResponse
from src.domain.exceptions import ReportNotFoundError, SampleNotFoundError
from src.domain.repositories import IUnitOfWork


@dataclass
class DownloadReportUseCase:
    """Use case for downloading saved PDF report."""

    uow: IUnitOfWork

    async def execute(self, sample_id: UUID) -> ReportBytesResponse:
        """Download saved PDF report.

        Args:
            sample_id: Sample UUID

        Returns:
            Report bytes response

        Raises:
            SampleNotFoundError: If sample not found
            ReportNotFoundError: If report not generated or file not found
        """
        async with self.uow:
            # Get sample
            sample = await self.uow.samples.get_by_id(sample_id)
            if not sample:
                raise SampleNotFoundError(str(sample_id))

            # Check report exists
            if not sample.report_path:
                raise ReportNotFoundError(f"Report not generated for sample {sample_id}")

            report_path = Path(sample.report_path)
            if not report_path.exists():
                raise ReportNotFoundError(f"Report file not found: {report_path}")

            # Read report file
            with open(report_path, "rb") as f:
                pdf_bytes = f.read()

            # Determine report type based on requires_resequencing flag
            is_resequencing_report = bool(sample.requires_resequencing)

            return ReportBytesResponse(
                sample_id=sample.id,
                sample_code=sample.sample_code,
                pdf_bytes=pdf_bytes,
                filename=f"{sample.sample_code}_report.pdf",
                is_resequencing_report=is_resequencing_report,
            )
