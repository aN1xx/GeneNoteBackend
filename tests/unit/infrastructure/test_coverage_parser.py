"""Tests for CoverageParser - parses coverage depth TSV files."""

import tempfile
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from src.infrastructure.pipeline.coverage_parser import CoverageParser


class TestCoverageParser:
    """Tests for CoverageParser."""

    @pytest.fixture
    def parser(self) -> CoverageParser:
        """Create parser instance."""
        return CoverageParser()

    @pytest.fixture
    def sample_id(self):
        """Create sample UUID."""
        return uuid4()

    def test_parse_file_success(self, parser: CoverageParser, sample_id) -> None:
        """Test successful parsing of coverage TSV file."""
        content = """0x_depth\t5x_depth\t30x_depth\t50x_depth\t100x_depth
100.0\t99.98\t95.5\t90.2\t75.3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            coverage = parser.parse_file(temp_path, sample_id)

            assert coverage.sample_id == sample_id
            assert coverage.depth_0x == Decimal("100.0")
            assert coverage.depth_5x == Decimal("99.98")
            assert coverage.depth_30x == Decimal("95.5")
            assert coverage.depth_50x == Decimal("90.2")
            assert coverage.depth_100x == Decimal("75.3")
            assert coverage.id is not None  # UUID generated
        finally:
            temp_path.unlink()

    def test_parse_file_integer_values(self, parser: CoverageParser, sample_id) -> None:
        """Test parsing with integer values (no decimal point)."""
        content = """0x_depth\t5x_depth\t30x_depth\t50x_depth\t100x_depth
100\t99\t95\t90\t75
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            coverage = parser.parse_file(temp_path, sample_id)

            assert coverage.depth_0x == Decimal("100")
            assert coverage.depth_5x == Decimal("99")
            assert coverage.depth_30x == Decimal("95")
            assert coverage.depth_50x == Decimal("90")
            assert coverage.depth_100x == Decimal("75")
        finally:
            temp_path.unlink()

    def test_parse_file_empty_returns_zeros(self, parser: CoverageParser, sample_id) -> None:
        """Test parsing file with only headers returns zero coverage."""
        content = """0x_depth\t5x_depth\t30x_depth\t50x_depth\t100x_depth
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            coverage = parser.parse_file(temp_path, sample_id)

            assert coverage.sample_id == sample_id
            assert coverage.depth_0x == Decimal("0")
            assert coverage.depth_5x == Decimal("0")
            assert coverage.depth_30x == Decimal("0")
            assert coverage.depth_50x == Decimal("0")
            assert coverage.depth_100x == Decimal("0")
        finally:
            temp_path.unlink()

    def test_parse_file_missing_columns(self, parser: CoverageParser, sample_id) -> None:
        """Test parsing when some columns are missing - uses default 0."""
        content = """0x_depth\t5x_depth\t30x_depth
100.0\t99.0\t95.0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            coverage = parser.parse_file(temp_path, sample_id)

            assert coverage.depth_0x == Decimal("100.0")
            assert coverage.depth_5x == Decimal("99.0")
            assert coverage.depth_30x == Decimal("95.0")
            assert coverage.depth_50x == Decimal("0")  # Missing column
            assert coverage.depth_100x == Decimal("0")  # Missing column
        finally:
            temp_path.unlink()

    def test_parse_decimal_valid(self, parser: CoverageParser) -> None:
        """Test decimal parsing with valid values."""
        assert parser._parse_decimal("100.0") == Decimal("100.0")
        assert parser._parse_decimal("99.98") == Decimal("99.98")
        assert parser._parse_decimal("0.5") == Decimal("0.5")
        assert parser._parse_decimal("0") == Decimal("0")

    def test_parse_decimal_invalid(self, parser: CoverageParser) -> None:
        """Test decimal parsing with invalid values returns 0."""
        assert parser._parse_decimal("") == Decimal("0")
        assert parser._parse_decimal(None) == Decimal("0")
        assert parser._parse_decimal("invalid") == Decimal("0")
        assert parser._parse_decimal("   ") == Decimal("0")

    def test_parse_file_whitespace_values(self, parser: CoverageParser, sample_id) -> None:
        """Test parsing when values have whitespace."""
        content = """0x_depth\t5x_depth\t30x_depth\t50x_depth\t100x_depth
  100.0  \t  99.98  \t  95.5  \t  90.2  \t  75.3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            coverage = parser.parse_file(temp_path, sample_id)

            # Values should be trimmed and parsed correctly
            assert coverage.depth_0x == Decimal("100.0")
            assert coverage.depth_5x == Decimal("99.98")
        finally:
            temp_path.unlink()

    def test_generates_unique_id(self, parser: CoverageParser, sample_id) -> None:
        """Test that coverage entity gets a unique UUID."""
        content = """0x_depth\t5x_depth\t30x_depth\t50x_depth\t100x_depth
100.0\t99.98\t95.5\t90.2\t75.3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            coverage1 = parser.parse_file(temp_path, sample_id)
            coverage2 = parser.parse_file(temp_path, sample_id)

            # Each parse should generate a new UUID
            assert coverage1.id != coverage2.id
        finally:
            temp_path.unlink()

    def test_realistic_pipeline_output(self, parser: CoverageParser, sample_id) -> None:
        """Test with realistic values from actual pipeline output."""
        # These values represent typical WES coverage metrics
        content = """0x_depth\t5x_depth\t30x_depth\t50x_depth\t100x_depth
99.87\t98.45\t92.31\t85.67\t65.23
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            coverage = parser.parse_file(temp_path, sample_id)

            # Verify precision is maintained
            assert coverage.depth_0x == Decimal("99.87")
            assert coverage.depth_5x == Decimal("98.45")
            assert coverage.depth_30x == Decimal("92.31")
            assert coverage.depth_50x == Decimal("85.67")
            assert coverage.depth_100x == Decimal("65.23")
        finally:
            temp_path.unlink()
