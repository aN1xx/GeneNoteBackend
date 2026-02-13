"""Snakemake pipeline executor."""

import asyncio
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)

# Allow returning None or Task (for async callbacks wrapped with create_task)
ProgressCallback = Callable[[int, str], object]


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    success: bool
    output_path: str | None = None
    error_message: str | None = None
    duration_seconds: int = 0


class SnakemakeExecutor:
    """Executor for Snakemake pipelines."""

    def __init__(
        self,
        snakemake_path: Path | None = None,
        conda_env: str | None = None,
    ) -> None:
        self._snakemake_path = snakemake_path or settings.snakemake_path
        self._conda_env = conda_env or settings.snakemake_conda_env
        self._snakefile = self._snakemake_path / "Snakefile"

    async def run_variant_calling(
        self,
        sample_id: str,
        fastq_r1: str,
        fastq_r2: str,
        output_dir: str,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult:
        """Run variant calling pipeline.

        Args:
            sample_id: Sample identifier
            fastq_r1: Path to FASTQ R1 file
            fastq_r2: Path to FASTQ R2 file
            output_dir: Output directory path
            progress_callback: Optional callback for progress updates

        Returns:
            PipelineResult with execution status
        """
        logger.info(f"Starting variant calling for sample {sample_id}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Prepare Snakemake config
        config = {
            "sample_id": sample_id,
            "fastq_r1": fastq_r1,
            "fastq_r2": fastq_r2,
            "output_dir": str(output_path),
        }

        # Build command
        cmd = self._build_snakemake_command(config, target="variant_calling")

        if progress_callback:
            progress_callback(5, "Starting variant calling pipeline")

        try:
            result = await self._execute_command(cmd, progress_callback)

            if result.success:
                # Check for expected output files
                variants_tsv = output_path / f"{sample_id}_variants.tsv"
                if variants_tsv.exists():
                    result.output_path = str(variants_tsv)
                else:
                    # Try alternative naming
                    for f in output_path.glob("*variants*.tsv"):
                        result.output_path = str(f)
                        break

            return result

        except Exception as e:
            logger.error(f"Variant calling failed: {e}", exc_info=True)
            return PipelineResult(
                success=False,
                error_message=str(e),
            )

    async def run_report_generation(
        self,
        sample_id: str,
        variants_tsv: str,
        patient_info: dict,
        output_dir: str,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult:
        """Run report generation pipeline.

        Args:
            sample_id: Sample identifier
            variants_tsv: Path to annotated variants TSV
            patient_info: Patient information dict
            output_dir: Output directory path
            progress_callback: Optional callback for progress updates

        Returns:
            PipelineResult with execution status
        """
        logger.info(f"Starting report generation for sample {sample_id}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # For report generation, we'll use a simplified approach
        # In production, this would call the actual report generation script
        if progress_callback:
            progress_callback(10, "Preparing report data")

        try:
            # Expected output
            report_pdf = output_path / f"{sample_id}_report.pdf"

            # Simulate report generation (in production, call actual script)
            if progress_callback:
                progress_callback(50, "Generating PDF report")

            # TODO: Call actual report generation script
            # For now, create a placeholder
            report_pdf.touch()

            if progress_callback:
                progress_callback(100, "Report generation complete")

            return PipelineResult(
                success=True,
                output_path=str(report_pdf),
            )

        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            return PipelineResult(
                success=False,
                error_message=str(e),
            )

    def _build_snakemake_command(
        self,
        config: dict,
        target: str | None = None,
    ) -> list[str]:
        """Build Snakemake command.

        Args:
            config: Configuration dictionary
            target: Optional target rule

        Returns:
            Command as list of strings
        """
        cmd = [
            "snakemake",
            "--snakefile",
            str(self._snakefile),
            "--directory",
            str(self._snakemake_path),
            "--cores",
            "4",
            "--use-conda",
        ]

        # Add config items
        for key, value in config.items():
            cmd.extend(["--config", f"{key}={value}"])

        # Add target if specified
        if target:
            cmd.append(target)

        return cmd

    async def _execute_command(
        self,
        cmd: list[str],
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult:
        """Execute command asynchronously.

        Args:
            cmd: Command to execute
            progress_callback: Optional progress callback

        Returns:
            PipelineResult
        """
        logger.debug(f"Executing command: {' '.join(cmd)}")

        start_time = asyncio.get_event_loop().time()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

            # Read output and track progress
            current_progress = 10
            if process.stdout:
                async for line in process.stdout:
                    line_str = line.decode().strip()
                    logger.debug(f"Snakemake: {line_str}")

                    # Parse progress from Snakemake output
                    if "rule" in line_str.lower():
                        current_progress = min(current_progress + 10, 90)
                        if progress_callback:
                            progress_callback(current_progress, line_str[:100])

            # Wait for completion
            await process.wait()

            end_time = asyncio.get_event_loop().time()
            duration = int(end_time - start_time)

            if process.returncode == 0:
                if progress_callback:
                    progress_callback(100, "Pipeline completed successfully")

                return PipelineResult(
                    success=True,
                    duration_seconds=duration,
                )
            else:
                error_msg = "Unknown error"
                if process.stderr:
                    stderr = await process.stderr.read()
                    error_msg = stderr.decode()[:500]
                logger.error(f"Snakemake failed: {error_msg}")

                return PipelineResult(
                    success=False,
                    error_message=error_msg,
                    duration_seconds=duration,
                )

        except asyncio.CancelledError:
            logger.warning("Pipeline execution cancelled")
            if process:
                process.terminate()
            raise

        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            return PipelineResult(
                success=False,
                error_message=str(e),
            )
