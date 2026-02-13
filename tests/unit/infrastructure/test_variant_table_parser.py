"""Tests for VariantTableParser - parses pipeline output TSV files."""

import tempfile
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from src.domain.enums import ACMGClassification
from src.infrastructure.pipeline.variant_table_parser import VariantTableParser


class TestVariantTableParser:
    """Tests for VariantTableParser."""

    @pytest.fixture
    def parser(self) -> VariantTableParser:
        """Create parser instance."""
        return VariantTableParser()

    @pytest.fixture
    def sample_id(self):
        """Create sample UUID."""
        return uuid4()

    @pytest.fixture
    def valid_tsv_content(self) -> str:
        """Valid TSV content matching pipeline output format."""
        return """chrom\tpos_GRCh38\tref\talt\tgene\tvariant_type\ttranscript\texon/intron\tHGVS_VariantName\tdepth\tgenotype\tPopFreq_GNOMAD_v3.1.2\tACMG_classification\tvariant_caller\tgatk_depth\tgatk_allele_depth\tgatk_allele_fraction\tvariant_db_num\tvariant_db_hetero_num\tvariant_db_homo_num\tartifact_db_num\tis_variant\tis_artifact
chr1\t12345\tA\tG\tBRCA1\tSNV\tNM_007294.4\texon 10\tc.1234A>G\t100\t0/1\t0.001\tПатогенный\tgatk\t100\t50\t0.5\t10\t7\t3\t0\t\t
chr2\t67890\tC\tT\tTP53\tMissense\tNM_000546.5\texon 5\tc.456C>T\t80\t1/1\t0.0001\tВариант неясного значения\tgatk,ngsep\t80\t75\t0.9375\t5\t3\t2\t1\t1\t0
"""

    def test_parse_file_success(
        self, parser: VariantTableParser, sample_id, valid_tsv_content: str
    ) -> None:
        """Test successful parsing of variants TSV file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(valid_tsv_content)
            temp_path = Path(f.name)

        try:
            variants = parser.parse_file(temp_path, sample_id)

            assert len(variants) == 2

            # First variant
            v1 = variants[0]
            assert v1.sample_id == sample_id
            assert v1.chromosome == "1"  # chr prefix removed
            assert v1.position == 12345
            assert v1.ref == "A"
            assert v1.alt == "G"
            assert v1.gene == "BRCA1"
            assert v1.variant_type == "SNV"
            assert v1.transcript == "NM_007294.4"
            assert v1.exon_intron == "exon 10"
            assert v1.hgvs == "c.1234A>G"
            assert v1.depth == 100
            assert v1.genotype == "0/1"
            assert v1.pop_freq_gnomad == Decimal("0.001")
            assert v1.acmg_classification == ACMGClassification.PATHOGENIC
            assert v1.variant_caller == "gatk"
            assert v1.gatk_depth == 100
            assert v1.gatk_allele_depth == 50
            assert v1.gatk_allele_fraction == Decimal("0.5")
            assert v1.variant_db_num == 10
            assert v1.variant_db_hetero_num == 7
            assert v1.variant_db_homo_num == 3
            assert v1.artifact_db_num == 0
            assert v1.is_variant is None  # Empty in TSV
            assert v1.is_artifact is None  # Empty in TSV

            # Second variant
            v2 = variants[1]
            assert v2.chromosome == "2"
            assert v2.position == 67890
            assert v2.gene == "TP53"
            assert v2.acmg_classification == ACMGClassification.VUS
            assert v2.variant_caller == "gatk,ngsep"
            assert v2.is_variant is True
            assert v2.is_artifact is False
        finally:
            temp_path.unlink()

    def test_parse_file_empty(self, parser: VariantTableParser, sample_id) -> None:
        """Test parsing empty file with only headers."""
        content = """chrom\tpos_GRCh38\tref\talt\tgene\tvariant_type\ttranscript\texon/intron\tHGVS_VariantName\tdepth\tgenotype\tPopFreq_GNOMAD_v3.1.2\tACMG_classification\tvariant_caller\tgatk_depth\tgatk_allele_depth\tgatk_allele_fraction\tvariant_db_num\tvariant_db_hetero_num\tvariant_db_homo_num\tartifact_db_num\tis_variant\tis_artifact
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            variants = parser.parse_file(temp_path, sample_id)
            assert len(variants) == 0
        finally:
            temp_path.unlink()

    def test_acmg_mapping_all_values(self, parser: VariantTableParser) -> None:
        """Test all ACMG classification mappings."""
        mappings = {
            "Патогенный": ACMGClassification.PATHOGENIC,
            "Вероятно патогенный": ACMGClassification.LIKELY_PATHOGENIC,
            "Вариант неясного значения": ACMGClassification.VUS,
            "Вариант неясного клинического значения": ACMGClassification.VUS,
            "Вероятно доброкачественный": ACMGClassification.LIKELY_BENIGN,
            "Доброкачественный": ACMGClassification.BENIGN,
        }

        for russian, expected_enum in mappings.items():
            assert parser.ACMG_MAPPING.get(russian) == expected_enum

    def test_clean_chrom(self, parser: VariantTableParser) -> None:
        """Test chromosome cleaning - removes 'chr' prefix."""
        assert parser._clean_chrom("chr1") == "1"
        assert parser._clean_chrom("CHR1") == "1"
        assert parser._clean_chrom("Chr1") == "1"
        assert parser._clean_chrom("1") == "1"
        assert parser._clean_chrom("chrX") == "X"
        assert parser._clean_chrom("X") == "X"

    def test_parse_int(self, parser: VariantTableParser) -> None:
        """Test integer parsing with various inputs."""
        assert parser._parse_int("100") == 100
        assert parser._parse_int("100.5") == 100  # Truncates float
        assert parser._parse_int("") == 0
        assert parser._parse_int(None) == 0
        assert parser._parse_int("invalid") == 0

    def test_parse_int_optional(self, parser: VariantTableParser) -> None:
        """Test optional integer parsing."""
        assert parser._parse_int_optional("100") == 100
        assert parser._parse_int_optional("") is None
        assert parser._parse_int_optional(None) is None
        assert parser._parse_int_optional("invalid") is None

    def test_parse_decimal(self, parser: VariantTableParser) -> None:
        """Test decimal parsing."""
        assert parser._parse_decimal("0.5") == Decimal("0.5")
        assert parser._parse_decimal("0.001") == Decimal("0.001")
        assert parser._parse_decimal("") is None
        assert parser._parse_decimal(None) is None
        assert parser._parse_decimal("invalid") is None

    def test_parse_bool(self, parser: VariantTableParser) -> None:
        """Test boolean parsing from various formats."""
        # True values
        assert parser._parse_bool("1") is True
        assert parser._parse_bool("true") is True
        assert parser._parse_bool("True") is True
        assert parser._parse_bool("yes") is True
        assert parser._parse_bool("да") is True

        # False values
        assert parser._parse_bool("0") is False
        assert parser._parse_bool("false") is False
        assert parser._parse_bool("False") is False
        assert parser._parse_bool("no") is False
        assert parser._parse_bool("нет") is False

        # None values
        assert parser._parse_bool("") is None
        assert parser._parse_bool(None) is None
        assert parser._parse_bool("unknown") is None

    def test_parse_file_with_missing_optional_fields(
        self, parser: VariantTableParser, sample_id
    ) -> None:
        """Test parsing when optional fields are missing."""
        content = """chrom\tpos_GRCh38\tref\talt\tgene\tvariant_type\ttranscript\texon/intron\tHGVS_VariantName\tdepth\tgenotype\tPopFreq_GNOMAD_v3.1.2\tACMG_classification\tvariant_caller\tgatk_depth\tgatk_allele_depth\tgatk_allele_fraction\tvariant_db_num\tvariant_db_hetero_num\tvariant_db_homo_num\tartifact_db_num\tis_variant\tis_artifact
1\t12345\tA\tG\tBRCA1\t\t\t\t\t50\t0/1\t\t\tgatk\t\t\t\t0\t0\t0\t0\t\t
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            variants = parser.parse_file(temp_path, sample_id)
            assert len(variants) == 1

            v = variants[0]
            assert v.chromosome == "1"
            assert v.position == 12345
            assert v.gene == "BRCA1"
            assert v.variant_type is None
            assert v.transcript == ""
            assert v.exon_intron is None
            assert v.hgvs is None
            assert v.pop_freq_gnomad is None
            assert v.acmg_classification is None
            assert v.gatk_depth is None
            assert v.gatk_allele_depth is None
            assert v.gatk_allele_fraction is None
        finally:
            temp_path.unlink()

    def test_generates_unique_ids(
        self, parser: VariantTableParser, sample_id, valid_tsv_content: str
    ) -> None:
        """Test that each variant gets a unique UUID."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(valid_tsv_content)
            temp_path = Path(f.name)

        try:
            variants = parser.parse_file(temp_path, sample_id)
            ids = [v.id for v in variants]
            assert len(ids) == len(set(ids))  # All unique
        finally:
            temp_path.unlink()
