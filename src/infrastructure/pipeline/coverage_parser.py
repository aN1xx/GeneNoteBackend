"""Parser for coverage depth files from Snakemake pipeline.

Parses the {sample}_CovWidthAtDepths.tsv file produced by make_VariantTable.py
"""

import csv
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from src.domain.entities import SampleCoverage


class CoverageParser:
    """Parser for coverage depth TSV files from pipeline output."""

    def parse_file(self, filepath: Path, sample_id: UUID) -> SampleCoverage:
        """Parse coverage depth TSV file and return SampleCoverage entity.

        Args:
            filepath: Path to the coverage TSV file (e.g., {sample}_CovWidthAtDepths.tsv)
            sample_id: UUID of the sample

        Returns:
            SampleCoverage domain entity

        File format example:
            0x_depth    5x_depth    30x_depth   50x_depth   100x_depth
            100.0       99.98       95.5        90.2        75.3
        """
        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")

            # Should have exactly one data row
            row = next(reader, None)
            if not row:
                # Return empty coverage if file is empty
                return SampleCoverage(
                    id=uuid4(),
                    sample_id=sample_id,
                    depth_0x=Decimal("0"),
                    depth_5x=Decimal("0"),
                    depth_30x=Decimal("0"),
                    depth_50x=Decimal("0"),
                    depth_100x=Decimal("0"),
                )

            return SampleCoverage(
                id=uuid4(),
                sample_id=sample_id,
                depth_0x=self._parse_decimal(row.get("0x_depth", "0")),
                depth_5x=self._parse_decimal(row.get("5x_depth", "0")),
                depth_30x=self._parse_decimal(row.get("30x_depth", "0")),
                depth_50x=self._parse_decimal(row.get("50x_depth", "0")),
                depth_100x=self._parse_decimal(row.get("100x_depth", "0")),
            )

    def _parse_decimal(self, value: str | None) -> Decimal:
        """Parse decimal value, defaulting to 0."""
        if not value or value.strip() == "":
            return Decimal("0")
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")
