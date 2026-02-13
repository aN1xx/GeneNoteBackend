"""Pipeline integration service.

Integrates the Snakemake variant calling pipeline with the backend.
"""

import asyncio
import gzip
import logging
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from src.config import settings
from src.domain.entities import Sample, SampleCoverage, SampleVariant
from src.infrastructure.pipeline.coverage_parser import CoverageParser
from src.infrastructure.pipeline.variant_table_parser import VariantTableParser

logger = logging.getLogger(__name__)

# Progress mapping for pipeline rules
PIPELINE_PROGRESS_RULES: dict[str, int] = {
    "rule trim_fastq": 20,
    "rule map_fastq": 30,
    "rule gatk_call_variants": 50,
    "rule ngsep_call_variants": 60,
    "rule xatlas_call_variants": 70,
    "rule make_variant_table": 85,
}


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""

    # Paths to pipeline scripts and data
    pipeline_base_path: Path
    pipeline_script: Path
    pipeline_config: Path
    results_path: Path
    databases_path: Path

    # Database files (used by Snakemake for variant/artifact lookups)
    variants_db: Path
    artifacts_db: Path

    # Reference files
    genome_fasta: Path

    # External tools
    ngsep_jar: Path
    vep_cache_dir: Path

    # VEP mode: False = online (database), True = offline (cache)
    vep_use_cache: bool = False

    @classmethod
    def from_settings(cls) -> "PipelineConfig":
        """Create config from application settings."""
        base_path = settings.pipeline_path

        return cls(
            pipeline_base_path=base_path,
            pipeline_script=base_path / "src" / "pipeline.py",
            pipeline_config=base_path / "src" / "pipeline_config.yaml",
            results_path=base_path / "results",
            databases_path=base_path / "data_bases",
            variants_db=base_path / "data_bases" / "GermlineVariants_DataBase.tsv",
            artifacts_db=base_path / "data_bases" / "GermlineArtifacts_DataBase.tsv",
            genome_fasta=base_path / "references" / "GRCh38" / "fasta_and_index" / "GRCh38.fa",
            ngsep_jar=Path("/opt/ngsep/NGSEPcore_5.0.0.jar"),
            vep_cache_dir=Path("/app/vep_cache"),
            vep_use_cache=True,  # Offline mode - uses local cache (download first)
        )


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    success: bool
    sample_code: str
    variants_file: Path | None = None
    coverage_file: Path | None = None
    error_message: str | None = None
    duration_seconds: int = 0


class PipelineService:
    """Service for executing variant calling pipeline."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        """Initialize pipeline service.

        Args:
            config: Pipeline configuration (default: from settings)
        """
        self.config = config or PipelineConfig.from_settings()
        self.variant_parser = VariantTableParser()
        self.coverage_parser = CoverageParser()

    def _is_gzip_file(self, filepath: Path) -> bool:
        """Check if a file is gzip compressed by reading magic bytes."""
        try:
            with open(filepath, "rb") as f:
                magic = f.read(2)
                return magic == b"\x1f\x8b"
        except Exception:
            return False

    def _copy_and_compress_if_needed(self, src: Path, dest: Path) -> None:
        """Copy file to destination, compressing if not already gzipped.

        Args:
            src: Source file path
            dest: Destination file path (should end with .gz)
        """
        if not src.exists():
            logger.warning(f"Source file does not exist: {src}")
            return

        # Skip if source and destination are the same file
        if src.resolve() == dest.resolve():
            logger.debug(f"Source and destination are the same file, skipping: {src}")
            return

        # Skip if destination already exists and has the same size
        if dest.exists() and dest.stat().st_size == src.stat().st_size:
            logger.debug(f"Destination file already exists with same size, skipping: {dest}")
            return

        if self._is_gzip_file(src):
            # File is already gzipped, just copy it
            logger.debug(f"File {src} is already gzipped, copying directly")
            shutil.copy2(src, dest)
        else:
            # File is not gzipped, compress it
            logger.info(f"Compressing {src} to {dest}")
            with open(src, "rb") as f_in, gzip.open(dest, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

    async def prepare_sample_for_pipeline(
        self,
        sample: Sample,
        fastq_r1_path: Path,
        fastq_r2_path: Path,
    ) -> Path:
        """Prepare sample files for pipeline execution.

        Creates the directory structure expected by the Snakemake pipeline.
        Handles both compressed and uncompressed FASTQ files.

        Args:
            sample: Sample entity
            fastq_r1_path: Path to R1 FASTQ file
            fastq_r2_path: Path to R2 FASTQ file

        Returns:
            Path to sample results directory
        """
        # Create sample directory structure
        sample_dir = self.config.results_path / sample.sample_code
        input_dir = sample_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        # Copy FASTQ files to input directory with expected naming
        # Pipeline expects: {sample}_S{number}_L001_R1_001.fastq.gz
        dest_r1 = input_dir / f"{sample.sample_code}_S1_L001_R1_001.fastq.gz"
        dest_r2 = input_dir / f"{sample.sample_code}_S1_L001_R2_001.fastq.gz"

        # Copy and compress if needed (handles uncompressed files with .gz extension)
        self._copy_and_compress_if_needed(fastq_r1_path, dest_r1)
        self._copy_and_compress_if_needed(fastq_r2_path, dest_r2)

        logger.info(f"Prepared sample {sample.sample_code} for pipeline in {sample_dir}")
        return sample_dir

    async def run_variant_calling(
        self,
        sample_code: str,
        progress_callback: Callable[[int, str], Any] | None = None,
    ) -> PipelineResult:
        """Run variant calling pipeline for a sample.

        Args:
            sample_code: Sample code (e.g., "12345" or "12345.2")
            progress_callback: Optional callback for progress updates

        Returns:
            PipelineResult with execution status and output paths
        """
        start_time = datetime.now(UTC)
        logger.info(f"Starting variant calling pipeline for sample {sample_code}")

        if progress_callback:
            await self._safe_callback(progress_callback, 5, "Initializing pipeline")

        try:
            # Run Snakemake pipeline
            cmd = self._build_snakemake_command(sample_code)
            logger.info(f"Snakemake command: {' '.join(cmd)}")
            logger.info(f"Working directory: {self.config.pipeline_base_path / 'src'}")

            if progress_callback:
                await self._safe_callback(progress_callback, 10, "Running Snakemake pipeline")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
                cwd=str(self.config.pipeline_base_path / "src"),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

            # Monitor progress - Snakemake outputs to stderr, so we merge it
            progress = 10
            output_lines: list[str] = []  # Keep last N lines for error reporting
            max_output_lines = 50

            if process.stdout:
                async for line in process.stdout:
                    line_str = line.decode().strip()
                    if line_str:
                        # Log important lines at INFO level for visibility
                        if any(
                            keyword in line_str.lower()
                            for keyword in [
                                "rule",
                                "error",
                                "warning",
                                "failed",
                                "job",
                                "finished",
                                "building dag",
                            ]
                        ):
                            logger.info(f"Pipeline: {line_str}")
                        else:
                            logger.debug(f"Pipeline: {line_str}")
                        output_lines.append(line_str)
                        if len(output_lines) > max_output_lines:
                            output_lines.pop(0)

                    progress = self._get_progress_from_line(line_str, progress)

                    if progress_callback:
                        await self._safe_callback(progress_callback, progress, line_str[:100])

            await process.wait()

            duration = int((datetime.now(UTC) - start_time).total_seconds())

            if process.returncode != 0:
                return await self._create_error_result(
                    sample_code, process, duration, "Pipeline execution failed", output_lines
                )

            return await self._create_success_result(sample_code, duration, progress_callback)

        except Exception as e:
            return self._create_exception_result(sample_code, e)

    def parse_pipeline_output(
        self,
        sample_id: UUID,
        variants_file: Path,
        coverage_file: Path | None,
    ) -> tuple[list[SampleVariant], SampleCoverage | None]:
        """Parse pipeline output files.

        Args:
            sample_id: Sample UUID
            variants_file: Path to variants TSV file
            coverage_file: Path to coverage TSV file (optional)

        Returns:
            Tuple of (variants list, coverage data)
        """
        variants = self.variant_parser.parse_file(variants_file, sample_id)

        coverage = None
        if coverage_file and coverage_file.exists():
            coverage = self.coverage_parser.parse_file(coverage_file, sample_id)

        return variants, coverage

    def _get_progress_from_line(self, line_str: str, current_progress: int) -> int:
        """Extract progress percentage from pipeline log line.

        Args:
            line_str: Log line from pipeline
            current_progress: Current progress value

        Returns:
            Updated progress value
        """
        rule_progress_map = {
            "rule trim_fastq": 20,
            "rule map_fastq": 30,
            "rule gatk_call_variants": 50,
            "rule ngsep_call_variants": 60,
            "rule xatlas_call_variants": 70,
            "rule make_variant_table": 85,
        }

        line_lower = line_str.lower()
        for rule, progress_value in rule_progress_map.items():
            if rule in line_lower:
                return progress_value

        return current_progress

    async def _create_error_result(
        self,
        sample_code: str,
        process: asyncio.subprocess.Process,
        duration: int,
        default_message: str,
        output_lines: list[str] | None = None,
    ) -> PipelineResult:
        """Create error result from failed process."""
        error_msg = f"{default_message} (exit code: {process.returncode})"
        logger.error(f"Pipeline failed for {sample_code}: {error_msg}")

        # Log last output lines at ERROR level for debugging
        if output_lines:
            logger.error(f"Last {len(output_lines)} lines of pipeline output:")
            for line in output_lines[-20:]:  # Show last 20 lines
                logger.error(f"  | {line}")

        return PipelineResult(
            success=False,
            sample_code=sample_code,
            error_message=error_msg,
            duration_seconds=duration,
        )

    async def _create_success_result(
        self,
        sample_code: str,
        duration: int,
        progress_callback: Callable[[int, str], Any] | None,
    ) -> PipelineResult:
        """Create success result with found output files."""
        sample_dir = self.config.results_path / sample_code
        variants_file = sample_dir / "variant_tables" / f"{sample_code}_variants_raw.tsv"
        coverage_file = sample_dir / "variant_tables" / f"{sample_code}_CovWidthAtDepths.tsv"

        if not variants_file.exists():
            return PipelineResult(
                success=False,
                sample_code=sample_code,
                error_message=f"Variants file not found: {variants_file}",
                duration_seconds=duration,
            )

        if progress_callback:
            await self._safe_callback(progress_callback, 100, "Pipeline completed")

        return PipelineResult(
            success=True,
            sample_code=sample_code,
            variants_file=variants_file,
            coverage_file=coverage_file if coverage_file.exists() else None,
            duration_seconds=duration,
        )

    def _create_exception_result(self, sample_code: str, exception: Exception) -> PipelineResult:
        """Create error result from exception."""
        logger.error(f"Pipeline execution error: {exception}", exc_info=True)
        return PipelineResult(
            success=False,
            sample_code=sample_code,
            error_message=str(exception),
        )

    def _create_runtime_config(self, sample_code: str) -> Path:
        """Create runtime config with absolute paths."""
        base_path = self.config.pipeline_base_path

        config_data = {
            "sample": sample_code,  # Pass sample code for single-sample processing
            "base_results_dirpath": str(self.config.results_path),
            "AnnotatedVariantDataBase_filepath": str(self.config.variants_db),
            "ArtifactsDataBase_filepath": str(self.config.artifacts_db),
            "genome_fasta_filepath": str(self.config.genome_fasta),
            "genome_FASTAIndex_prefix": str(
                base_path / "references" / "GRCh38" / "index_bwa-mem" / "GRCh38"
            ),
            "PrimerCoords_bed_filepath": str(
                base_path / "references" / "primers_Quasar-BRCA" / "primers_Quasar-BRCA.bed"
            ),
            "VariantCallingIntervals_filepath": str(
                base_path / "references" / "Quasar-BRCA_intervals" / "Quasar-BRCA_intervals.bed"
            ),
            "genes_bed_filepath": str(
                base_path / "references" / "gene_intervals" / "BRCA_genes.bed"
            ),
            "ngsep_jar_filepath": str(self.config.ngsep_jar),
            "vep_cache_dir": str(self.config.vep_cache_dir),
            "vep_use_cache": self.config.vep_use_cache,  # False = online mode, True = offline with cache
            "FlagsFixing_script_filepath": str(base_path / "src" / "fix_BAM_flags.py"),
            "xatlas_merging_script_filepath": str(base_path / "src" / "merge_xAtlas_VCFs.py"),
            "MakingVariantTable_script_filepath": str(base_path / "src" / "make_VariantTable.py"),
        }

        # Write to temp file
        config_path = self.config.results_path / sample_code / "runtime_config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        logger.info(f"Created runtime config at {config_path}")
        return config_path

    def _build_snakemake_command(self, sample_code: str) -> list[str]:
        """Build Snakemake command for a specific sample."""
        runtime_config = self._create_runtime_config(sample_code)

        return [
            "snakemake",
            "--snakefile",
            str(self.config.pipeline_script),
            "--configfile",
            str(runtime_config),
            "--default-resources",
            "mem_mb=30",
            "--printshellcmds",
            "--cores",
            "4",
            "--nolock",
            "--no-hooks",
            "--drop-metadata",  # Avoid conda env tracking issues
            "--rerun-incomplete",  # Handle interrupted runs
            # Target specific sample
            f"{self.config.results_path}/{sample_code}/variant_tables/{sample_code}_variants_raw.tsv",
        ]

    async def _safe_callback(
        self,
        callback: Callable[[int, str], Any],
        progress: int,
        message: str,
    ) -> None:
        """Safely call progress callback."""
        try:
            result = callback(progress, message)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")
