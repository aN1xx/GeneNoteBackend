"""Report utilities."""

import json
import logging
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)


def get_fastp_stats(sample_code: str) -> dict | None:
    """Get fastp statistics from pipeline results.

    Reads the fastp JSON report generated during trimming step.

    Args:
        sample_code: Sample code (e.g., "58133863" or "58133863.2")

    Returns:
        Parsed fastp JSON dict or None if not found/error
    """
    # Path: {pipeline_path}/results/{sample_code}/trimming/{sample_code}_trimming_report.json
    # Also check backend repo pipeline folder
    possible_paths = [
        settings.pipeline_path
        / "results"
        / sample_code
        / "trimming"
        / f"{sample_code}_trimming_report.json",
        Path(__file__).parent.parent.parent.parent.parent
        / "pipeline"
        / "results"
        / sample_code
        / "trimming"
        / f"{sample_code}_trimming_report.json",
    ]

    for fastp_path in possible_paths:
        if fastp_path.exists():
            try:
                with open(fastp_path) as f:
                    stats = json.load(f)
                logger.info(f"Loaded fastp stats from {fastp_path}")
                return stats
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read fastp stats from {fastp_path}: {e}")
                continue

    logger.debug(f"Fastp stats not found for sample {sample_code}")
    return None


def get_logo_path() -> str | None:
    """Get logo path from config or pipeline folder.

    Searches for the logo in the following order:
    1. Explicit config setting (pdf_logo_path)
    2. Backend repo pipeline folder (pipeline/src/olymp_logo.pdf)
    3. Configured pipeline path (pipeline_path/src/olymp_logo.pdf)

    Returns:
        Path to logo file or None if not found
    """
    # First check config
    if settings.pdf_logo_path and settings.pdf_logo_path.exists():
        return str(settings.pdf_logo_path)

    # Fallback to backend repo pipeline folder
    pipeline_logo = (
        Path(__file__).parent.parent.parent.parent.parent / "pipeline" / "src" / "olymp_logo.pdf"
    )
    if pipeline_logo.exists():
        return str(pipeline_logo)

    # Try from configured pipeline path
    if settings.pipeline_path:
        logo_in_pipeline = settings.pipeline_path / "src" / "olymp_logo.pdf"
        if logo_in_pipeline.exists():
            return str(logo_in_pipeline)

    return None
