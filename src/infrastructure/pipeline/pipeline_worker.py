"""Pipeline worker for executing Snakemake pipelines."""

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pysam

from src.application.use_cases.report import GenerateReportUseCase
from src.domain.entities import FileRecord
from src.domain.enums import FileType, PipelineType, SampleStatus
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.infrastructure.kafka import (
    KafkaProducer,
    PipelineCompletedEvent,
    PipelineFailedEvent,
    PipelineProgressEvent,
    PipelineStartedEvent,
)
from src.infrastructure.pipeline.pipeline_service import PipelineConfig, PipelineService

logger = logging.getLogger(__name__)


class PipelineWorker:
    """Worker for processing pipeline commands.

    Integrates with the Snakemake variant calling pipeline to:
    1. Run variant calling (GATK, NGSEP, xAtlas)
    2. Parse output files (variants TSV, coverage TSV)
    3. Store results in database
    4. Generate PDF reports
    """

    def __init__(
        self,
        kafka_producer: KafkaProducer,
        pipeline_config: PipelineConfig | None = None,
    ) -> None:
        self._kafka_producer = kafka_producer
        self._pipeline_service = PipelineService(pipeline_config)

    async def handle_pipeline_start(self, event_data: dict[str, Any]) -> None:
        """Handle pipeline start command.

        Args:
            event_data: Event data from Kafka containing:
                - pipeline_id: UUID of the pipeline run
                - sample_id: UUID of the sample
                - pipeline_type: Type of pipeline (variant_calling or report_generation)
                - sample_code: Sample code (e.g., "12345" or "12345.2")
                - fastq_r1_path: Path to R1 FASTQ (for variant_calling)
                - fastq_r2_path: Path to R2 FASTQ (for variant_calling)
        """
        pipeline_id = UUID(event_data["pipeline_id"])
        sample_id = UUID(event_data["sample_id"])
        pipeline_type = PipelineType(event_data["pipeline_type"])
        sample_code = event_data.get("sample_code", "")

        logger.info(f"Starting pipeline {pipeline_id} ({pipeline_type}) for sample {sample_code}")

        # Send started event and update database
        await self._send_started_event(pipeline_id, sample_id, pipeline_type)
        await self._update_pipeline_run_started(pipeline_id)

        try:
            if pipeline_type == PipelineType.VARIANT_CALLING:
                await self._run_variant_calling(
                    pipeline_id=pipeline_id,
                    sample_id=sample_id,
                    sample_code=sample_code,
                    fastq_r1=event_data.get("fastq_r1_path", ""),
                    fastq_r2=event_data.get("fastq_r2_path", ""),
                )
            elif pipeline_type == PipelineType.REPORT_GENERATION:
                await self._run_report_generation(
                    pipeline_id=pipeline_id,
                    sample_id=sample_id,
                    sample_code=sample_code,
                )

        except asyncio.CancelledError:
            logger.warning(f"Pipeline {pipeline_id} was cancelled")
            raise

        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} failed: {e}", exc_info=True)
            await self._send_failed_event(
                pipeline_id=pipeline_id,
                sample_id=sample_id,
                pipeline_type=pipeline_type,
                error_message=str(e),
            )
            await self._update_pipeline_run_failed(pipeline_id, str(e))

    async def _run_variant_calling(
        self,
        pipeline_id: UUID,
        sample_id: UUID,
        sample_code: str,
        fastq_r1: str,
        fastq_r2: str,
    ) -> None:
        """Run variant calling pipeline.

        Executes the full Snakemake workflow:
        1. Trim FASTQ with fastp
        2. Map with bwa mem
        3. Call variants with GATK, NGSEP, xAtlas
        4. Normalize VCFs with bcftools
        5. Create variant table with make_VariantTable.py

        Args:
            pipeline_id: Pipeline run ID
            sample_id: Sample ID
            sample_code: Sample code for file naming
            fastq_r1: Path to R1 FASTQ
            fastq_r2: Path to R2 FASTQ
        """
        start_time = datetime.now(UTC)

        # Get sample and prepare for pipeline
        uow = SQLAlchemyUnitOfWork(async_session_factory)
        async with uow:
            sample = await uow.samples.get_by_id(sample_id)
            if not sample:
                raise ValueError(f"Sample {sample_id} not found")

            # Prepare sample files for pipeline
            await self._pipeline_service.prepare_sample_for_pipeline(
                sample=sample,
                fastq_r1_path=Path(fastq_r1),
                fastq_r2_path=Path(fastq_r2),
            )

        # Progress callback
        async def on_progress(percent: int, message: str) -> None:
            await self._send_progress_event(pipeline_id, percent, message)

        # Run Snakemake variant calling
        result = await self._pipeline_service.run_variant_calling(
            sample_code=sample_code,
            progress_callback=on_progress,
        )

        if result.success and result.variants_file:
            # Parse and load variants + coverage
            await self._load_pipeline_output(
                sample_id=sample_id,
                variants_file=result.variants_file,
                coverage_file=result.coverage_file,
            )

            # Save pipeline output files (BAM, VCF, etc.) to database
            await self._save_pipeline_files(
                sample_id=sample_id,
                sample_code=sample_code,
            )

            duration = int((datetime.now(UTC) - start_time).total_seconds())

            # Update sample status
            await self._update_sample_status(
                sample_id=sample_id,
                status=SampleStatus.AWAITING_ANNOTATION,
            )

            await self._send_completed_event(
                pipeline_id=pipeline_id,
                sample_id=sample_id,
                pipeline_type=PipelineType.VARIANT_CALLING,
                output_path=str(result.variants_file),
                duration_seconds=duration,
            )
            await self._update_pipeline_run_completed(pipeline_id, str(result.variants_file))
        else:
            # Update sample status to failed
            await self._update_sample_status(
                sample_id=sample_id,
                status=SampleStatus.FAILED,
            )

            error_msg = result.error_message or "Unknown error"
            await self._send_failed_event(
                pipeline_id=pipeline_id,
                sample_id=sample_id,
                pipeline_type=PipelineType.VARIANT_CALLING,
                error_message=error_msg,
            )
            await self._update_pipeline_run_failed(pipeline_id, error_msg)

    async def _run_report_generation(
        self,
        pipeline_id: UUID,
        sample_id: UUID,
        sample_code: str,
    ) -> None:
        """Run report generation using GenerateReportUseCase.

        Generates PDF report from PostgreSQL data:
        1. Gets confirmed variants from sample_variants table
        2. Gets patient info and coverage data
        3. Generates PDF report using ReportGenerator

        Args:
            pipeline_id: Pipeline run ID
            sample_id: Sample ID
            sample_code: Sample code (unused, kept for API compatibility)
        """
        start_time = datetime.now(UTC)

        await self._send_progress_event(pipeline_id, 10, "Starting report generation")

        try:
            uow = SQLAlchemyUnitOfWork(async_session_factory)
            use_case = GenerateReportUseCase(uow=uow)

            await self._send_progress_event(pipeline_id, 30, "Generating PDF report")

            result = await use_case.execute(sample_id)

            duration = int((datetime.now(UTC) - start_time).total_seconds())

            await self._send_progress_event(pipeline_id, 100, "Report generated")

            await self._send_completed_event(
                pipeline_id=pipeline_id,
                sample_id=sample_id,
                pipeline_type=PipelineType.REPORT_GENERATION,
                output_path=result.report_path,
                duration_seconds=duration,
            )
            await self._update_pipeline_run_completed(pipeline_id, result.report_path)

        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            await self._send_failed_event(
                pipeline_id=pipeline_id,
                sample_id=sample_id,
                pipeline_type=PipelineType.REPORT_GENERATION,
                error_message=str(e),
            )
            await self._update_pipeline_run_failed(pipeline_id, str(e))

    async def _load_pipeline_output(
        self,
        sample_id: UUID,
        variants_file: Path,
        coverage_file: Path | None,
    ) -> None:
        """Load variants and coverage from pipeline output to database.

        Args:
            sample_id: Sample ID
            variants_file: Path to variants TSV
            coverage_file: Path to coverage TSV (optional)
        """
        logger.info(f"Loading pipeline output from {variants_file}")

        # Parse pipeline output
        variants, coverage = self._pipeline_service.parse_pipeline_output(
            sample_id=sample_id,
            variants_file=variants_file,
            coverage_file=coverage_file,
        )

        if not variants:
            logger.warning("No variants found in pipeline output")
            return

        # Store in database
        uow = SQLAlchemyUnitOfWork(async_session_factory)
        async with uow:
            # Save variants
            await uow.sample_variants.save_many(variants)
            logger.info(f"Saved {len(variants)} variants for sample {sample_id}")

            # Save coverage if available
            if coverage:
                await uow.sample_coverages.upsert(coverage)
                logger.info(f"Saved coverage data for sample {sample_id}")

                # Update sample coverage quality
                sample = await uow.samples.get_by_id(sample_id)
                if sample:
                    # Consider quality passed if >=90% at 30x depth
                    sample.coverage_quality_passed = coverage.depth_30x >= 90
                    sample.processed_at = datetime.now(UTC)
                    await uow.samples.save(sample)

            await uow.commit()

    async def _save_pipeline_files(  # noqa: PLR0915
        self,
        sample_id: UUID,
        sample_code: str,
    ) -> None:
        """Save pipeline output files (BAM, VCF, etc.) to database.

        Args:
            sample_id: Sample UUID
            sample_code: Sample code for constructing file paths
        """
        logger.info(f"Saving pipeline files for sample {sample_code}")
        sample_dir = self._pipeline_service.config.results_path / sample_code

        file_records: list[FileRecord] = []

        # BAM file
        bam_path = sample_dir / "mapping" / f"{sample_code}_PrimersClipped_FlagsFixed_filtered.bam"
        bai_path = sample_dir / "mapping" / f"{sample_code}_PrimersClipped_FlagsFixed_filtered.bai"

        if bam_path.exists():
            file_record = await self._create_file_record(
                sample_id=sample_id,
                file_path=bam_path,
                file_type=FileType.BAM,
            )
            if file_record:
                file_records.append(file_record)

            # Create BAM index if it doesn't exist
            if not bai_path.exists():
                logger.info(f"BAM index not found for {bam_path}, creating it...")
                try:
                    await self._create_bam_index(bam_path, bai_path)
                    logger.info(f"Successfully created BAM index: {bai_path}")
                except Exception as e:
                    logger.warning(f"Failed to create BAM index for {bam_path}: {e}")

        # BAM index (save if exists, whether created now or already existed)
        if bai_path.exists():
            file_record = await self._create_file_record(
                sample_id=sample_id,
                file_path=bai_path,
                file_type=FileType.BAM_INDEX,
            )
            if file_record:
                file_records.append(file_record)

        # GATK VCF
        gatk_vcf_path = (
            sample_dir
            / "variant_calling"
            / "gatk"
            / f"{sample_code}_GATK_normalized_VEPAnnotated.vcf"
        )
        if gatk_vcf_path.exists():
            file_record = await self._create_file_record(
                sample_id=sample_id,
                file_path=gatk_vcf_path,
                file_type=FileType.VCF_GATK,
            )
            if file_record:
                file_records.append(file_record)

        # NGSEP VCF
        ngsep_vcf_path = (
            sample_dir
            / "variant_calling"
            / "ngsep"
            / f"{sample_code}_NGSEP_IntervalsSelected_normalized.vcf"
        )
        if ngsep_vcf_path.exists():
            file_record = await self._create_file_record(
                sample_id=sample_id,
                file_path=ngsep_vcf_path,
                file_type=FileType.VCF_NGSEP,
            )
            if file_record:
                file_records.append(file_record)

        # xAtlas VCF
        xatlas_vcf_path = (
            sample_dir
            / "variant_calling"
            / "xatlas"
            / f"{sample_code}_xAtlas_merged_IntervalsSelected_normalized.vcf"
        )
        if xatlas_vcf_path.exists():
            file_record = await self._create_file_record(
                sample_id=sample_id,
                file_path=xatlas_vcf_path,
                file_type=FileType.VCF_XATLAS,
            )
            if file_record:
                file_records.append(file_record)

        # Fastp HTML report (rename to _fastp_report.html for downloads)
        fastp_html_path = sample_dir / "trimming" / f"{sample_code}_trimming_report.html"
        if fastp_html_path.exists():
            file_record = await self._create_file_record(
                sample_id=sample_id,
                file_path=fastp_html_path,
                file_type=FileType.HTML_FASTP_REPORT,
                custom_filename=f"{sample_code}_fastp_report.html",
            )
            if file_record:
                file_records.append(file_record)

        # Save all file records
        if file_records:
            uow = SQLAlchemyUnitOfWork(async_session_factory)
            async with uow:
                # Check if files already exist and update or create
                for file_record in file_records:
                    existing = await uow.file_records.get_by_sample_and_type(
                        sample_id=sample_id,
                        file_type=file_record.file_type,
                    )
                    if existing:
                        # Update existing record
                        existing.file_path = file_record.file_path
                        existing.file_name = file_record.file_name
                        existing.file_size = file_record.file_size
                        existing.checksum_md5 = file_record.checksum_md5
                        await uow.file_records.save(existing)
                    else:
                        # Create new record
                        await uow.file_records.save(file_record)
                await uow.commit()
                logger.info(f"Saved {len(file_records)} pipeline files for sample {sample_code}")

    async def _create_file_record(
        self,
        sample_id: UUID,
        file_path: Path,
        file_type: FileType,
        custom_filename: str | None = None,
    ) -> FileRecord | None:
        """Create FileRecord entity from file path.

        Args:
            sample_id: Sample UUID
            file_path: Path to file
            file_type: File type
            custom_filename: Optional custom filename (defaults to file_path.name)

        Returns:
            FileRecord entity or None if file doesn't exist
        """
        if not file_path.exists():
            return None

        try:
            # Get file size
            file_size = file_path.stat().st_size

            # Calculate MD5 checksum
            checksum_md5 = await self._calculate_md5(file_path)

            # Get file name (use custom if provided)
            file_name = custom_filename or file_path.name

            return FileRecord(
                id=uuid4(),
                sample_id=sample_id,
                file_type=file_type,
                file_path=str(file_path),
                file_name=file_name,
                file_size=file_size,
                checksum_md5=checksum_md5,
                uploaded_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.error(f"Error creating file record for {file_path}: {e}")
            return None

    async def _create_bam_index(self, bam_path: Path, bai_path: Path) -> None:
        """Create BAM index file if it doesn't exist.

        Args:
            bam_path: Path to BAM file
            bai_path: Path where BAM index should be created

        Raises:
            Exception: If index creation fails
        """
        # Run indexing in executor to avoid blocking
        # pysam.index creates index with .bai extension automatically in the same directory
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            pysam.index,  # type: ignore[attr-defined]
            str(bam_path),
        )
        # pysam.index creates index with .bai extension automatically
        # Verify the index was created at the expected location
        if not bai_path.exists():
            raise FileNotFoundError(
                f"BAM index was not created at {bai_path} after indexing {bam_path}"
            )

    async def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            MD5 checksum as hex string
        """
        hash_md5 = hashlib.md5()
        # Read file in chunks to avoid memory issues with large files
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def _update_sample_status(
        self,
        sample_id: UUID,
        status: SampleStatus,
    ) -> None:
        """Update sample status in database."""
        uow = SQLAlchemyUnitOfWork(async_session_factory)
        async with uow:
            sample = await uow.samples.get_by_id(sample_id)
            if sample:
                sample.status = status
                await uow.samples.save(sample)
                await uow.commit()

    async def _update_pipeline_run_started(self, pipeline_id: UUID) -> None:
        """Update pipeline run status to RUNNING in database."""
        uow = SQLAlchemyUnitOfWork(async_session_factory)
        async with uow:
            run = await uow.pipelines.get_by_id(pipeline_id)
            if run and not run.is_terminal:
                run.start()
                await uow.pipelines.save(run)
                await uow.commit()
                logger.info(f"Pipeline {pipeline_id} marked as running")

    async def _update_pipeline_run_completed(self, pipeline_id: UUID, output_path: str) -> None:
        """Update pipeline run status to COMPLETED in database."""
        uow = SQLAlchemyUnitOfWork(async_session_factory)
        async with uow:
            run = await uow.pipelines.get_by_id(pipeline_id)
            if run and run.is_active:
                run.complete(output_path)
                await uow.pipelines.save(run)
                await uow.commit()
                logger.info(f"Pipeline {pipeline_id} marked as completed")

    async def _update_pipeline_run_failed(self, pipeline_id: UUID, error_message: str) -> None:
        """Update pipeline run status to FAILED in database."""
        uow = SQLAlchemyUnitOfWork(async_session_factory)
        async with uow:
            run = await uow.pipelines.get_by_id(pipeline_id)
            if run and not run.is_terminal:
                run.fail(error_message)
                await uow.pipelines.save(run)
                await uow.commit()
                logger.info(f"Pipeline {pipeline_id} marked as failed")

    async def _send_started_event(
        self,
        pipeline_id: UUID,
        sample_id: UUID,
        pipeline_type: PipelineType,
    ) -> None:
        """Send pipeline started event."""
        event = PipelineStartedEvent(
            timestamp=datetime.now(UTC),
            pipeline_id=pipeline_id,
            sample_id=sample_id,
            pipeline_type=pipeline_type,
        )
        await self._kafka_producer.send_pipeline_event(event)

    async def _send_progress_event(
        self,
        pipeline_id: UUID,
        percent: int,
        message: str | None = None,
    ) -> None:
        """Send pipeline progress event."""
        event = PipelineProgressEvent(
            timestamp=datetime.now(UTC),
            pipeline_id=pipeline_id,
            progress_percent=percent,
            message=message,
        )
        await self._kafka_producer.send_pipeline_event(event)

    async def _send_completed_event(
        self,
        pipeline_id: UUID,
        sample_id: UUID,
        pipeline_type: PipelineType,
        output_path: str,
        duration_seconds: int,
    ) -> None:
        """Send pipeline completed event."""
        event = PipelineCompletedEvent(
            timestamp=datetime.now(UTC),
            pipeline_id=pipeline_id,
            sample_id=sample_id,
            pipeline_type=pipeline_type,
            output_path=output_path,
            duration_seconds=duration_seconds,
        )
        await self._kafka_producer.send_pipeline_event(event)

    async def _send_failed_event(
        self,
        pipeline_id: UUID,
        sample_id: UUID,
        pipeline_type: PipelineType,
        error_message: str,
    ) -> None:
        """Send pipeline failed event."""
        event = PipelineFailedEvent(
            timestamp=datetime.now(UTC),
            pipeline_id=pipeline_id,
            sample_id=sample_id,
            pipeline_type=pipeline_type,
            error_message=error_message,
        )
        await self._kafka_producer.send_pipeline_event(event)
