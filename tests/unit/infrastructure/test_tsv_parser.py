"""Tests for TSV parser."""

import tempfile
from pathlib import Path

import pytest

from src.domain.enums import Sex, VariantType
from src.infrastructure.pipeline.tsv_parser import TSVParser


class TestTSVParser:
    """Tests for TSVParser."""

    @pytest.fixture
    def parser(self) -> TSVParser:
        """Create TSV parser."""
        return TSVParser()

    def test_parse_patients_tsv_success(self, parser: TSVParser) -> None:
        """Test parsing patients TSV file."""
        content = """ФИО\tПол\tДата_рождения\tНомер_заявки\tНаименование_исследования
Test Patient\tМ\t15.01.1990\tREQ-001\tWES Analysis
Another Patient\tЖ\t20.05.1985\tREQ-002\tPanel
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            patients = parser.parse_patients_tsv(temp_path)

            assert len(patients) == 2
            assert patients[0].name == "Test Patient"
            assert patients[0].sex == Sex.MALE
            assert patients[0].request_id == "REQ-001"

            assert patients[1].name == "Another Patient"
            assert patients[1].sex == Sex.FEMALE
        finally:
            Path(temp_path).unlink()

    def test_parse_patients_file_not_found(self, parser: TSVParser) -> None:
        """Test parsing non-existent file."""
        patients = parser.parse_patients_tsv("/nonexistent/file.tsv")
        assert patients == []

    def test_parse_variants_tsv_success(self, parser: TSVParser) -> None:
        """Test parsing variants TSV file."""
        content = """Chr\tПозиция\tRef\tAlt\tГен\tТип\tТранскрипт\tЭкзон/интрон\tHGVS\tЗиготность\tГлубина_покрытия\tВариантные_колеры\tGATK_глубина\tGATK_число_альтернативных_ридов\tGATK_частота_альтернативного_аллеля\tЧисло_в_базе_вариантов\tЧисло_гетерозигот_в_базе\tЧисло_гомозигот_в_базе\tЧисло_в_базе_артефактов
1\t12345\tA\tG\tBRCA1\tSNV\tNM_007294.4\texon 10\tc.1234A>G\t0/1\t100\tGATK\t100\t50\t0.5\t10\t7\t3\t0
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            variants = parser.parse_variants_tsv(temp_path)

            assert len(variants) == 1
            variant = variants[0]
            assert variant.chromosome == "1"
            assert variant.position == 12345
            assert variant.ref == "A"
            assert variant.alt == "G"
            assert variant.gene == "BRCA1"
            assert variant.variant_type == VariantType.SNV
        finally:
            Path(temp_path).unlink()

    def test_parse_variants_file_not_found(self, parser: TSVParser) -> None:
        """Test parsing non-existent variants file."""
        variants = parser.parse_variants_tsv("/nonexistent/file.tsv")
        assert variants == []

    def test_parse_variant_row_missing_required_fields(self, parser: TSVParser) -> None:
        """Test parsing variant with missing required fields."""
        content = """Chr\tПозиция\tRef\tAlt
\t12345\tA\tG
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            variants = parser.parse_variants_tsv(temp_path)
            assert len(variants) == 0
        finally:
            Path(temp_path).unlink()

    def test_safe_int(self, parser: TSVParser) -> None:
        """Test safe integer conversion."""
        assert parser._safe_int("100") == 100
        assert parser._safe_int("100.5") == 100
        assert parser._safe_int("") == 0
        assert parser._safe_int(None) == 0
        assert parser._safe_int("invalid") == 0

    def test_safe_decimal(self, parser: TSVParser) -> None:
        """Test safe decimal conversion."""
        from decimal import Decimal

        assert parser._safe_decimal("0.5") == Decimal("0.5")
        assert parser._safe_decimal("") is None
        assert parser._safe_decimal(None) is None
        assert parser._safe_decimal("invalid") is None
