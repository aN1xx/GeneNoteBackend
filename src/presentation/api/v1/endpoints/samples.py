"""Sample API endpoints."""

import io
import zipfile
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response

from src.application.dto.sample import (
    CreateSampleRequest,
    SampleCoverageResponse,
    SampleListResponse,
    SampleResponse,
    UploadFilesResponse,
)
from src.application.use_cases.sample import (
    CreateSampleUseCase,
    GetAllSamplesUseCase,
    GetAwaitingAnnotationSamplesUseCase,
    GetSampleByCodeUseCase,
    GetSampleCoverageUseCase,
    GetSamplesByPatientUseCase,
    GetSampleUseCase,
    RequestResequencingUseCase,
)
from src.config import settings
from src.domain.enums import FileType
from src.domain.exceptions import SampleNotFoundError
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.presentation.dependencies import (
    CurrentUser,
    GeneticistUser,
    LaborantUser,
)

router = APIRouter(prefix="/samples", tags=["Samples"])


def get_uow() -> SQLAlchemyUnitOfWork:
    """Get Unit of Work instance."""
    return SQLAlchemyUnitOfWork(async_session_factory)


@router.post(
    "",
    response_model=SampleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create sample",
    description="Create a new sample for a patient",
)
async def create_sample(
    request: CreateSampleRequest,
    current_user: LaborantUser,
) -> SampleResponse:
    """Create a new sample."""
    use_case = CreateSampleUseCase(uow=get_uow())
    return await use_case.execute(request)


@router.get(
    "",
    response_model=SampleListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all samples",
    description="Get list of all samples with pagination",
)
async def get_all_samples(
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SampleListResponse:
    """Get all samples."""
    use_case = GetAllSamplesUseCase(uow=get_uow())
    return await use_case.execute(limit=limit, offset=offset)


@router.get(
    "/awaiting-annotation",
    response_model=SampleListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get samples awaiting annotation",
    description="Get list of samples that need annotation",
)
async def get_awaiting_annotation(
    current_user: GeneticistUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SampleListResponse:
    """Get samples awaiting annotation."""
    use_case = GetAwaitingAnnotationSamplesUseCase(uow=get_uow())
    return await use_case.execute(limit=limit, offset=offset)


@router.get(
    "/by-code/{sample_code}",
    response_model=SampleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sample by code",
    description="Get sample by its unique code",
)
async def get_sample_by_code(
    sample_code: str,
    current_user: CurrentUser,
) -> SampleResponse:
    """Get sample by code."""
    use_case = GetSampleByCodeUseCase(uow=get_uow())
    return await use_case.execute(sample_code)


@router.get(
    "/by-patient/{patient_id}",
    response_model=SampleListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get samples by patient",
    description="Get all samples for a patient",
)
async def get_samples_by_patient(
    patient_id: UUID,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SampleListResponse:
    """Get samples by patient ID."""
    use_case = GetSamplesByPatientUseCase(uow=get_uow())
    return await use_case.execute(patient_id=patient_id, limit=limit, offset=offset)


@router.get(
    "/{sample_id}",
    response_model=SampleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sample",
    description="Get sample by ID",
)
async def get_sample(
    sample_id: UUID,
    current_user: CurrentUser,
) -> SampleResponse:
    """Get sample by ID."""
    use_case = GetSampleUseCase(uow=get_uow())
    return await use_case.execute(sample_id)


@router.get(
    "/{sample_id}/coverage",
    response_model=SampleCoverageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sample coverage",
    description="Get coverage statistics for a sample",
)
async def get_sample_coverage(
    sample_id: UUID,
    current_user: CurrentUser,
) -> SampleCoverageResponse:
    """Get coverage statistics for a sample."""
    use_case = GetSampleCoverageUseCase(uow=get_uow())
    return await use_case.execute(sample_id)


@router.post(
    "/{sample_id}/upload-files",
    response_model=UploadFilesResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload sample files",
    description="Upload FASTQ and TSV files for a sample",
)
async def upload_sample_files(
    sample_id: UUID,
    current_user: LaborantUser,
    fastq_r1: UploadFile = File(..., description="FASTQ R1 file"),
    fastq_r2: UploadFile = File(..., description="FASTQ R2 file"),
    tsv_patients: UploadFile | None = File(None, description="TSV patients file"),
) -> UploadFilesResponse:
    """Upload files for a sample."""
    uow = get_uow()

    async with uow:
        # Get sample
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            from src.domain.exceptions import SampleNotFoundError

            raise SampleNotFoundError(str(sample_id))

        # Create directory for sample files (use sample_code/request_id, not UUID)
        sample_dir = settings.file_storage_path / sample.sample_code
        sample_dir.mkdir(parents=True, exist_ok=True)

        # Save FASTQ R1
        r1_path = sample_dir / f"{sample.sample_code}_R1.fastq.gz"
        async with aiofiles.open(r1_path, "wb") as f:
            content = await fastq_r1.read()
            await f.write(content)

        # Save FASTQ R2
        r2_path = sample_dir / f"{sample.sample_code}_R2.fastq.gz"
        async with aiofiles.open(r2_path, "wb") as f:
            content = await fastq_r2.read()
            await f.write(content)

        # Save TSV if provided
        tsv_path = None
        if tsv_patients:
            tsv_path = sample_dir / f"{sample.sample_code}_patients.tsv"
            async with aiofiles.open(tsv_path, "wb") as f:
                content = await tsv_patients.read()
                await f.write(content)

        # Update sample with file paths
        sample.set_fastq_paths(str(r1_path), str(r2_path))
        if tsv_path:
            sample.tsv_patients_path = str(tsv_path)

        await uow.samples.save(sample)
        await uow.commit()

        return UploadFilesResponse(
            sample_id=sample.id,
            fastq_r1_path=str(r1_path),
            fastq_r2_path=str(r2_path),
            tsv_patients_path=str(tsv_path) if tsv_path else None,
            status=sample.status,
        )


@router.get(
    "/{sample_id}/download/bam",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Download BAM file",
    description="Скачать BAM файл для образца",
)
async def download_bam_file(
    sample_id: UUID,
    current_user: CurrentUser,
) -> FileResponse:
    """Download BAM file for a sample."""
    uow = get_uow()

    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        bam_file = await uow.file_records.get_by_sample_and_type(
            sample_id=sample_id,
            file_type=FileType.BAM,
        )

        if not bam_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BAM файл не найден для образца {sample_id}",
            )

        file_path = Path(bam_file.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BAM файл не найден на диске: {bam_file.file_path}",
            )

        return FileResponse(
            path=str(file_path),
            filename=bam_file.file_name,
            media_type="application/octet-stream",
        )


@router.get(
    "/{sample_id}/download/vcf",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Download VCF file",
    description="Скачать VCF файл для образца (gatk, ngsep, xatlas)",
)
async def download_vcf_file(
    sample_id: UUID,
    current_user: CurrentUser,
    variant_caller: str = Query(default="gatk", description="Variant caller: gatk, ngsep, xatlas"),
) -> FileResponse:
    """Download VCF file for a sample.

    Args:
        sample_id: Sample UUID
        variant_caller: Variant caller type (gatk, ngsep, xatlas). Default: gatk
        current_user: Current authenticated user

    Returns:
        VCF file response

    Raises:
        HTTPException: If sample or VCF file not found
    """
    uow = get_uow()

    # Map variant caller to file type
    variant_caller_lower = variant_caller.lower()
    file_type_map = {
        "gatk": FileType.VCF_GATK,
        "ngsep": FileType.VCF_NGSEP,
        "xatlas": FileType.VCF_XATLAS,
    }

    if variant_caller_lower not in file_type_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный variant caller: {variant_caller}. Допустимые значения: gatk, ngsep, xatlas",
        )

    file_type = file_type_map[variant_caller_lower]

    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        vcf_file = await uow.file_records.get_by_sample_and_type(
            sample_id=sample_id,
            file_type=file_type,
        )

        if not vcf_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VCF файл ({variant_caller}) не найден для образца {sample_id}",
            )

        file_path = Path(vcf_file.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VCF файл не найден на диске: {vcf_file.file_path}",
            )

        return FileResponse(
            path=str(file_path),
            filename=vcf_file.file_name,
            media_type="text/vcf",
        )


@router.get(
    "/{sample_id}/download/bam-index",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Download BAM index file",
    description="Скачать индекс BAM файла (.bai) для образца",
)
async def download_bam_index_file(
    sample_id: UUID,
    current_user: CurrentUser,
) -> FileResponse:
    """Download BAM index file for a sample."""
    uow = get_uow()

    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        bai_file = await uow.file_records.get_by_sample_and_type(
            sample_id=sample_id,
            file_type=FileType.BAM_INDEX,
        )

        if not bai_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BAM индекс не найден для образца {sample_id}",
            )

        file_path = Path(bai_file.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BAM индекс не найден на диске: {bai_file.file_path}",
            )

        return FileResponse(
            path=str(file_path),
            filename=bai_file.file_name,
            media_type="application/octet-stream",
        )


@router.get(
    "/{sample_id}/download/all-files",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Download all pipeline files as ZIP archive",
    description="Скачать все файлы пайплайна (BAM, BAI, VCF GATK, VCF NGSEP, VCF xAtlas, fastp report) в одном ZIP архиве",
)
async def download_all_pipeline_files(
    sample_id: UUID,
    current_user: CurrentUser,
) -> Response:
    """Download all pipeline files (BAM, BAI, 3 VCF files, fastp HTML report) as a ZIP archive.

    Args:
        sample_id: Sample UUID
        current_user: Current authenticated user

    Returns:
        ZIP archive containing all pipeline files

    Raises:
        HTTPException: If sample not found or files are missing
    """
    uow = get_uow()

    async with uow:
        # Get sample
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        # Define required file types (must be present)
        required_files = {
            "BAM": FileType.BAM,
            "BAM_INDEX": FileType.BAM_INDEX,
            "VCF_GATK": FileType.VCF_GATK,
            "VCF_NGSEP": FileType.VCF_NGSEP,
            "VCF_XATLAS": FileType.VCF_XATLAS,
        }

        # Optional files (included if available)
        optional_files = {
            "HTML_FASTP_REPORT": FileType.HTML_FASTP_REPORT,
        }

        # Get all file records
        files_to_archive: list[tuple[Path, str]] = []
        missing_files = []

        # Check required files
        for file_name, file_type in required_files.items():
            file_record = await uow.file_records.get_by_sample_and_type(
                sample_id=sample_id,
                file_type=file_type,
            )

            if not file_record:
                missing_files.append(file_name)
                continue

            file_path = Path(file_record.file_path)
            if not file_path.exists():
                missing_files.append(f"{file_name} (файл не найден на диске)")
                continue

            files_to_archive.append((file_path, file_record.file_name))

        if missing_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Не найдены следующие файлы для образца {sample_id}: {', '.join(missing_files)}",
            )

        # Add optional files if available
        for _file_name, file_type in optional_files.items():
            file_record = await uow.file_records.get_by_sample_and_type(
                sample_id=sample_id,
                file_type=file_type,
            )

            if file_record:
                file_path = Path(file_record.file_path)
                if file_path.exists():
                    files_to_archive.append((file_path, file_record.file_name))

        if not files_to_archive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Файлы пайплайна не найдены для образца {sample_id}",
            )

        # Create ZIP archive in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add each file to the archive
            for file_path, file_name in files_to_archive:
                zip_file.write(
                    str(file_path),  # Convert Path to str for zipfile
                    arcname=file_name,  # Use original filename in archive
                )

        zip_buffer.seek(0)
        zip_bytes = zip_buffer.read()

        # Create archive filename
        archive_filename = f"{sample.sample_code}_pipeline_files.zip"

        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{archive_filename}"',
                "Content-Length": str(len(zip_bytes)),
            },
        )


@router.post(
    "/{sample_id}/request-resequencing",
    response_model=SampleResponse,
    status_code=status.HTTP_200_OK,
    summary="Request resequencing",
    description="Mark sample as requiring resequencing and generate resequencing notice PDF report (geneticist only)",
)
async def request_resequencing(
    sample_id: UUID,
    current_user: GeneticistUser,
) -> SampleResponse:
    """Request resequencing for a sample.

    This endpoint:
    1. Validates sample is in AWAITING_ANNOTATION or ANNOTATED status
    2. Generates resequencing notice PDF report
    3. Sets sample status to REPORT_GENERATED
    4. Marks sample as requiring resequencing

    The generated PDF report will be available via GET /api/v1/reports/samples/{sample_id}/download
    """
    use_case = RequestResequencingUseCase(uow=get_uow())
    return await use_case.execute(sample_id, current_user.id)
