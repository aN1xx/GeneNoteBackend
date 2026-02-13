"""Upload API endpoints for file uploads."""

import csv
import logging
import re
from datetime import UTC, datetime
from datetime import date as date_type
from datetime import datetime as dt
from io import StringIO
from pathlib import Path
from uuid import UUID, uuid4

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from src.application.dto.pipeline import StartPipelineRequest
from src.application.use_cases.pipeline import StartPipelineUseCase
from src.config import settings
from src.domain.entities import Patient, Sample
from src.domain.enums import PipelineType, SampleStatus, Sex
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.infrastructure.kafka import get_kafka_producer
from src.presentation.dependencies import LaborantUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])


class UploadResponse(BaseModel):
    """Response for successful upload."""

    message: str
    samples_created: int
    sample_ids: list[str]
    pipelines_started: int


class TSVValidationError(BaseModel):
    """Error response for TSV validation."""

    error: str
    detail: str


def get_uow() -> SQLAlchemyUnitOfWork:
    """Get Unit of Work instance."""
    return SQLAlchemyUnitOfWork(async_session_factory)


def parse_date(date_str: str) -> date_type | None:
    """Parse date from various formats."""
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    # Try ISO format
    if "-" in date_str:
        try:
            return date_type.fromisoformat(date_str)
        except ValueError:
            pass

    # Try Russian format
    formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y.%m.%d"]
    for fmt in formats:
        try:
            return dt.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def _validate_tsv_rows(rows: list[dict]) -> str | None:
    """Validate TSV rows for required data."""
    for i, row in enumerate(rows, start=2):
        if not row.get("name", "").strip():
            return f"Строка {i}: отсутствует имя пациента"
        if not row.get("request_id", "").strip():
            return f"Строка {i}: отсутствует номер заявки"
        if not row.get("birth_date", "").strip():
            return f"Строка {i}: отсутствует дата рождения"
        if not parse_date(row.get("birth_date", "")):
            return f"Строка {i}: некорректный формат даты рождения"
    return None


def _normalize_column_names(rows: list[dict]) -> list[dict]:
    """Normalize column names: strip whitespace, remove BOM, apply aliases.

    Args:
        rows: List of row dicts from CSV reader

    Returns:
        List of rows with normalized column names
    """
    # Column aliases mapping (alternative name -> standard name)
    column_aliases = {
        # name alternatives
        "patient_name": "name",
        "patient": "name",
        "фио": "name",
        "имя": "name",
        "пациент": "name",
        "\ufeffname": "name",  # BOM + name
        # sex alternatives
        "gender": "sex",
        "пол": "sex",
        "\ufeffsex": "sex",
        # birth_date alternatives
        "birthdate": "birth_date",
        "дата_рождения": "birth_date",
        "дата рождения": "birth_date",
        "др": "birth_date",
        "\ufeffbirth_date": "birth_date",
        # request_id alternatives
        "requestid": "request_id",
        "request": "request_id",
        "заявка": "request_id",
        "номер_заявки": "request_id",
        "номер заявки": "request_id",
        "\ufeffrequest_id": "request_id",
        # analysis_name alternatives
        "analysisname": "analysis_name",
        "analysis": "analysis_name",
        "анализ": "analysis_name",
        "название_анализа": "analysis_name",
        "\ufeffanalysis_name": "analysis_name",
    }

    normalized_rows = []
    for row in rows:
        normalized_row = {}
        for key, value in row.items():
            # Normalize key: strip whitespace, remove BOM
            normalized_key = key.strip().replace("\ufeff", "").lower()

            # Check for alias
            if normalized_key in column_aliases:
                normalized_key = column_aliases[normalized_key]
            elif key.strip().replace("\ufeff", "") in column_aliases:
                # Try original case
                normalized_key = column_aliases[key.strip().replace("\ufeff", "")]
            else:
                # Use original key (preserving case for standard columns)
                normalized_key = key.strip().replace("\ufeff", "")

            normalized_row[normalized_key] = value
        normalized_rows.append(normalized_row)

    return normalized_rows


def validate_tsv_content(content: str) -> tuple[list[dict], str | None]:
    """Validate TSV content and return parsed rows."""
    # Remove BOM from content if present
    content = content.replace("\ufeff", "")

    try:
        reader = csv.DictReader(StringIO(content), delimiter="\t")
        rows = list(reader)
    except Exception as e:
        return [], f"Файл не является валидным TSV: {e}"

    if len(rows) < 1:
        return [], "Файл не содержит данных образцов"

    if len(rows) > 100:
        return [], "Файл содержит более 100 образцов"

    # Normalize column names (handle BOM, aliases, whitespace)
    rows = _normalize_column_names(rows)

    # Check required columns
    required_columns = {"name", "sex", "birth_date", "request_id", "analysis_name"}
    if rows:
        first_row_keys = set(rows[0].keys())
        missing = required_columns - first_row_keys
        if missing:
            return [], f"Отсутствуют обязательные колонки: {', '.join(missing)}"

    # Validate each row
    error = _validate_tsv_rows(rows)
    if error:
        return [], error

    return rows, None


def _extract_sample_name(filename: str) -> str:
    """Extract sample name from FASTQ filename."""
    match = re.match(r"^(.+?)_R[12]", filename)
    if match:
        sample_name = match.group(1)
        return re.sub(r"_S\d+.*$", "", sample_name)
    return filename.split("_")[0]


def _validate_fastq_extensions(fastq_files: list[UploadFile]) -> str | None:
    """Validate FASTQ file extensions."""
    for f in fastq_files:
        if not f.filename:
            return "FASTQ файл без имени"
        if not f.filename.endswith((".fastq.gz", ".fq.gz", ".fastq", ".fq")):
            return f"Файл {f.filename} не является FASTQ файлом"
    return None


def _group_fastq_by_sample(fastq_files: list[UploadFile]) -> dict[str, list[str]]:
    """Group FASTQ files by sample name."""
    fastq_samples: dict[str, list[str]] = {}
    for f in fastq_files:
        if f.filename:
            sample_name = _extract_sample_name(f.filename)
            if sample_name not in fastq_samples:
                fastq_samples[sample_name] = []
            fastq_samples[sample_name].append(f.filename)
    return fastq_samples


def validate_fastq_files(fastq_files: list[UploadFile], tsv_rows: list[dict]) -> str | None:
    """Validate FASTQ files against TSV data."""
    if len(fastq_files) == 0:
        return "FASTQ файлы не загружены"

    if len(fastq_files) % 2 != 0:
        return "Количество FASTQ файлов должно быть четным (R1 и R2 для каждого образца)"

    ext_error = _validate_fastq_extensions(fastq_files)
    if ext_error:
        return ext_error

    request_ids = {row["request_id"].strip() for row in tsv_rows}
    fastq_samples = _group_fastq_by_sample(fastq_files)

    # Check matching
    for sample_name in fastq_samples:
        if sample_name not in request_ids:
            return f"FASTQ файлы для образца '{sample_name}' не соответствуют данным в TSV"

    for request_id in request_ids:
        if request_id not in fastq_samples:
            return f"Отсутствуют FASTQ файлы для образца '{request_id}'"
        if len(fastq_samples[request_id]) != 2:
            return f"Образец '{request_id}' должен иметь ровно 2 FASTQ файла (R1 и R2)"

    return None


async def _generate_unique_request_id(uow: SQLAlchemyUnitOfWork, request_id: str) -> str:
    """Generate unique request_id by adding postfix if needed."""
    existing = await uow.patients.get_by_request_id(request_id)
    if not existing:
        return request_id

    base_request_id = request_id.split(".")[0]
    count = 2
    new_request_id = f"{base_request_id}.{count}"
    while await uow.patients.request_id_exists(new_request_id):
        count += 1
        new_request_id = f"{base_request_id}.{count}"
    return new_request_id


async def _create_patient_and_sample(
    uow: SQLAlchemyUnitOfWork,
    row: dict,
    user_id: UUID,
    upload_time: datetime,
) -> Sample:
    """Create patient and sample from TSV row."""
    request_id = await _generate_unique_request_id(uow, row["request_id"].strip())

    birth_date = parse_date(row["birth_date"])
    if not birth_date:
        msg = f"Некорректная дата рождения для пациента {row['name']}"
        raise ValueError(msg)

    patient = Patient(
        id=uuid4(),
        name=row["name"].strip(),
        sex=Sex.from_string(row.get("sex", "").strip()),
        birth_date=birth_date,
        request_id=request_id,
        analysis_name=row.get("analysis_name", "").strip(),
        analysis_date=upload_time.date(),
    )
    await uow.patients.save(patient)

    sample = Sample(
        id=uuid4(),
        patient_id=patient.id,
        sample_code=request_id,
        status=SampleStatus.UPLOADED,
        uploaded_at=upload_time,
        uploaded_by_id=user_id,
    )
    await uow.samples.save(sample)
    return sample


async def _save_fastq_files(
    sample: Sample,
    fastq_files: list[UploadFile],
    uow: SQLAlchemyUnitOfWork,
) -> None:
    """Save FASTQ files for a sample."""
    sample_dir = settings.file_storage_path / sample.sample_code
    sample_dir.mkdir(parents=True, exist_ok=True)

    original_request_id = sample.sample_code.split(".")[0]
    logger.info(
        f"Saving FASTQ files for sample {sample.sample_code}, looking for request_id: {original_request_id}"
    )
    logger.info(f"Available FASTQ files: {[f.filename for f in fastq_files]}")

    for fastq in fastq_files:
        if not fastq.filename or original_request_id not in fastq.filename:
            logger.debug(f"Skipping file {fastq.filename} - does not match {original_request_id}")
            continue

        dest_path = _get_fastq_dest_path(sample_dir, sample.sample_code, fastq.filename)
        if not dest_path:
            continue

        await fastq.seek(0)
        content = await fastq.read()
        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(content)

        await _update_sample_fastq_path(uow, sample.id, fastq.filename, dest_path)


def _get_fastq_dest_path(sample_dir: Path, sample_code: str, filename: str) -> Path | None:
    """Get destination path for FASTQ file."""
    if "_R1" in filename:
        return sample_dir / f"{sample_code}_R1.fastq.gz"
    if "_R2" in filename:
        return sample_dir / f"{sample_code}_R2.fastq.gz"
    return None


async def _update_sample_fastq_path(
    uow: SQLAlchemyUnitOfWork,
    sample_id: UUID,
    filename: str,
    dest_path: Path,
) -> None:
    """Update sample with FASTQ file path."""
    async with uow:
        db_sample = await uow.samples.get_by_id(sample_id)
        if db_sample:
            if "_R1" in filename:
                db_sample.fastq_r1_path = str(dest_path)
            else:
                db_sample.fastq_r2_path = str(dest_path)
            await uow.samples.save(db_sample)
            await uow.commit()


async def _start_pipelines_for_samples(sample_ids: list[UUID]) -> list[UUID]:
    """Start variant calling pipelines for uploaded samples.

    Returns list of sample IDs for which pipeline was successfully started.
    """
    started_pipelines: list[UUID] = []

    try:
        kafka_producer = await get_kafka_producer()
        logger.info("Kafka producer available for auto-starting pipelines")
    except Exception as e:
        logger.warning(f"Kafka producer unavailable, pipelines not auto-started: {e}")
        return started_pipelines

    for sample_id in sample_ids:
        try:
            use_case = StartPipelineUseCase(
                uow=get_uow(),
                kafka_producer=kafka_producer,
            )
            request = StartPipelineRequest(
                sample_id=sample_id,
                pipeline_type=PipelineType.VARIANT_CALLING,
            )
            logger.info(f"Attempting to start pipeline for sample {sample_id}")
            await use_case.execute(request)
            started_pipelines.append(sample_id)
            logger.info(f"Auto-started variant calling pipeline for sample {sample_id}")
        except Exception as e:
            logger.error(
                f"Failed to auto-start pipeline for sample {sample_id}: {e}", exc_info=True
            )

    return started_pipelines


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload samples",
    description="Upload TSV file with patient data and FASTQ files for processing",
    responses={
        400: {"model": TSVValidationError, "description": "Validation error"},
    },
)
async def upload_samples(
    current_user: LaborantUser,
    tsv_file: UploadFile = File(..., description="TSV file with patient data"),
    fastq_files: list[UploadFile] = File(..., description="FASTQ files (R1 and R2 pairs)"),
) -> UploadResponse:
    """Upload TSV and FASTQ files to create samples and start processing."""
    # Validate TSV file extension
    if not tsv_file.filename or not tsv_file.filename.endswith(".tsv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Расширение файла не является .tsv",
        )

    # Read and validate TSV content
    tsv_content = await tsv_file.read()
    try:
        tsv_text = tsv_content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл не является валидным TSV (ошибка кодировки)",
        ) from e

    tsv_rows, error = validate_tsv_content(tsv_text)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    error = validate_fastq_files(fastq_files, tsv_rows)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    uow = get_uow()
    created_samples: list[Sample] = []
    upload_time = datetime.now(UTC)

    # Create patients and samples
    async with uow:
        for row in tsv_rows:
            sample = await _create_patient_and_sample(uow, row, current_user.id, upload_time)
            created_samples.append(sample)
        await uow.commit()

    # Save FASTQ files
    for sample in created_samples:
        await _save_fastq_files(sample, fastq_files, uow)

    # Save TSV file
    if created_samples:
        tsv_dir = settings.file_storage_path / "tsv_uploads"
        tsv_dir.mkdir(parents=True, exist_ok=True)
        tsv_path = tsv_dir / f"{upload_time.strftime('%Y%m%d_%H%M%S')}_patients.tsv"
        async with aiofiles.open(tsv_path, "wb") as f:
            await f.write(tsv_content)

    # Auto-start variant calling pipelines
    sample_ids = [s.id for s in created_samples]
    started = await _start_pipelines_for_samples(sample_ids)

    return UploadResponse(
        message=f"Успешно загружено {len(created_samples)} образцов, запущено {len(started)} пайплайнов",
        samples_created=len(created_samples),
        sample_ids=[str(s.id) for s in created_samples],
        pipelines_started=len(started),
    )
