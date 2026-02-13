"""Tests for domain value objects."""

import pytest

from src.domain.value_objects import VariantName
from src.domain.value_objects.genomic_position import GenomicCoordinate, GenomicPosition


class TestGenomicPosition:
    """Tests for GenomicPosition value object."""

    def test_create_valid_position(self) -> None:
        """Test creating valid genomic position."""
        pos = GenomicPosition(value=12345)
        assert pos.value == 12345

    def test_invalid_position_negative(self) -> None:
        """Test invalid position raises error."""
        with pytest.raises(ValueError):
            GenomicPosition(value=-1)

    def test_invalid_position_zero(self) -> None:
        """Test zero position raises error (1-based coordinates)."""
        with pytest.raises(ValueError):
            GenomicPosition(value=0)

    def test_equality(self) -> None:
        """Test position equality."""
        pos1 = GenomicPosition(value=12345)
        pos2 = GenomicPosition(value=12345)
        pos3 = GenomicPosition(value=12346)

        assert pos1 == pos2
        assert pos1 != pos3

    def test_string_representation(self) -> None:
        """Test string representation."""
        pos = GenomicPosition(value=12345)
        assert str(pos) == "12345"

    def test_int_conversion(self) -> None:
        """Test integer conversion."""
        pos = GenomicPosition(value=12345)
        assert int(pos) == 12345


class TestGenomicCoordinate:
    """Tests for GenomicCoordinate value object."""

    def test_create_valid_coordinate(self) -> None:
        """Test creating valid genomic coordinate."""
        coord = GenomicCoordinate(chromosome="1", position=12345)
        assert coord.chromosome == "1"
        assert coord.position == 12345

    def test_normalize_chromosome(self) -> None:
        """Test chromosome normalization (removes 'chr' prefix)."""
        coord = GenomicCoordinate(chromosome="chr1", position=12345)
        assert coord.chromosome == "1"

    def test_string_representation(self) -> None:
        """Test string representation."""
        coord = GenomicCoordinate(chromosome="1", position=12345)
        assert str(coord) == "chr1:12345"


class TestVariantName:
    """Tests for VariantName value object."""

    def test_create_variant_name(self) -> None:
        """Test creating variant name."""
        name = VariantName(
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
        )
        assert name.chromosome == "1"
        assert name.position == 12345
        assert name.ref == "A"
        assert name.alt == "G"

    def test_string_representation(self) -> None:
        """Test string representation."""
        name = VariantName(
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
        )
        assert str(name) == "chr1-12345-A-G"

    def test_from_string(self) -> None:
        """Test creating from string."""
        name = VariantName.from_string("chr1-12345-A-G")
        assert name.chromosome == "1"
        assert name.position == 12345
        assert name.ref == "A"
        assert name.alt == "G"

    def test_from_string_without_chr_prefix(self) -> None:
        """Test creating from string without chr prefix."""
        name = VariantName.from_string("1-12345-A-G")
        assert name.chromosome == "1"
        assert name.position == 12345

    def test_equality(self) -> None:
        """Test variant name equality."""
        name1 = VariantName(chromosome="1", position=12345, ref="A", alt="G")
        name2 = VariantName(chromosome="1", position=12345, ref="A", alt="G")
        name3 = VariantName(chromosome="1", position=12345, ref="A", alt="T")

        assert name1 == name2
        assert name1 != name3

    def test_is_snv(self) -> None:
        """Test SNV detection."""
        snv = VariantName(chromosome="1", position=12345, ref="A", alt="G")
        assert snv.is_snv is True

        indel = VariantName(chromosome="1", position=12345, ref="A", alt="AG")
        assert indel.is_snv is False

    def test_is_insertion(self) -> None:
        """Test insertion detection."""
        insertion = VariantName(chromosome="1", position=12345, ref="A", alt="AG")
        assert insertion.is_insertion is True

    def test_is_deletion(self) -> None:
        """Test deletion detection."""
        deletion = VariantName(chromosome="1", position=12345, ref="AG", alt="A")
        assert deletion.is_deletion is True
