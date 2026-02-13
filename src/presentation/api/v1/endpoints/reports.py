"""Report API endpoints for generating PDF reports."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from src.application.dto.report import GenerateReportResponse
from src.application.use_cases.report import (
    DownloadReportUseCase,
    GenerateReportUseCase,
    PreviewReportUseCase,
)
from src.domain.repositories import IUnitOfWork
from src.presentation.dependencies import CurrentUser, GeneticistUser, get_unit_of_work

router = APIRouter(prefix="/reports", tags=["Reports"])

# Type alias for dependency injection
UoW = Annotated[IUnitOfWork, Depends(get_unit_of_work)]


@router.post(
    "/samples/{sample_id}/generate",
    response_model=GenerateReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate report",
    description="Generate PDF report for an annotated sample",
)
async def generate_report(
    sample_id: UUID,
    uow: UoW,
    current_user: GeneticistUser,
) -> GenerateReportResponse:
    """Generate PDF report for a sample."""
    use_case = GenerateReportUseCase(uow=uow)
    return await use_case.execute(sample_id)


@router.get(
    "/samples/{sample_id}/download",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Download report",
    description="Download generated PDF report for a sample",
)
async def download_report(
    sample_id: UUID,
    uow: UoW,
    current_user: CurrentUser,
) -> Response:
    """Download PDF report for a sample."""
    use_case = DownloadReportUseCase(uow=uow)
    result = await use_case.execute(sample_id)

    report_type = "resequencing" if result.is_resequencing_report else "annotated"

    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Report-Type": report_type,
        },
    )


@router.get(
    "/samples/{sample_id}/preview",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Preview report",
    description="Generate and preview report without saving (for samples in ANNOTATED status)",
)
async def preview_report(
    sample_id: UUID,
    uow: UoW,
    current_user: GeneticistUser,
) -> Response:
    """Preview PDF report for a sample (generates on-the-fly without saving)."""
    use_case = PreviewReportUseCase(uow=uow)
    result = await use_case.execute(sample_id)

    report_type = "resequencing" if result.is_resequencing_report else "annotated"

    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{result.filename}"',
            "X-Report-Type": report_type,
        },
    )
