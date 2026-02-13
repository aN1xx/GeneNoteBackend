"""Tests for variant loader."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.domain.entities import GermlineArtifact, GermlineVariant, RawVariant
from src.domain.enums import VariantType
from src.infrastructure.pipeline.variant_loader import VariantLoader


class TestVariantLoader:
    """Tests for VariantLoader."""

    @pytest.fixture
    def loader(self, mock_uow: MagicMock) -> VariantLoader:
        """Create variant loader with mocked UoW."""
        return VariantLoader(mock_uow)

    @pytest.fixture
    def raw_variant(self) -> RawVariant:
        """Create a raw variant for testing."""
        return RawVariant(
            id=uuid4(),
            sample_id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            exon_intron="exon 10",
            hgvs="c.1234A>G",
            genotype="0/1",
            depth=100,
            variant_caller="GATK",
            gatk_depth=100,
            gatk_allele_depth=50,
            gatk_allele_fraction=Decimal("0.5"),
            variant_db_num=10,
            variant_db_hetero_num=7,
            variant_db_homo_num=3,
            artifact_db_num=0,
        )

    @pytest.mark.asyncio
    async def test_load_new_variant(
        self,
        loader: VariantLoader,
        mock_uow: MagicMock,
        raw_variant: RawVariant,
    ) -> None:
        """Test loading new variant."""
        mock_uow.variants.get_by_coordinates = AsyncMock(return_value=None)
        mock_uow.variants.save = AsyncMock()
        mock_uow.artifacts.get_by_coordinates = AsyncMock(return_value=None)

        sample_id = uuid4()
        patient_id = uuid4()

        stats = await loader.load_raw_variants(
            raw_variants=[raw_variant],
            sample_id=sample_id,
            patient_id=patient_id,
        )

        assert stats["total"] == 1
        assert stats["new_variants"] == 1
        assert stats["updated_variants"] == 0
        mock_uow.variants.save.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_existing_variant(
        self,
        loader: VariantLoader,
        mock_uow: MagicMock,
        raw_variant: RawVariant,
        sample_variant: GermlineVariant,
    ) -> None:
        """Test loading existing variant updates statistics."""
        mock_uow.variants.get_by_coordinates = AsyncMock(return_value=sample_variant)
        mock_uow.variants.save = AsyncMock()
        mock_uow.artifacts.get_by_coordinates = AsyncMock(return_value=None)

        sample_id = uuid4()
        patient_id = uuid4()

        initial_sample_num = sample_variant.sample_num

        stats = await loader.load_raw_variants(
            raw_variants=[raw_variant],
            sample_id=sample_id,
            patient_id=patient_id,
        )

        assert stats["total"] == 1
        assert stats["new_variants"] == 0
        assert stats["updated_variants"] == 1
        # Verify statistics were updated
        assert sample_variant.sample_num == initial_sample_num + 1

    @pytest.mark.asyncio
    async def test_load_variant_with_artifact(
        self,
        loader: VariantLoader,
        mock_uow: MagicMock,
    ) -> None:
        """Test loading variant that triggers artifact creation."""
        raw_variant = RawVariant(
            id=uuid4(),
            sample_id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            genotype="0/1",
            depth=100,
            variant_caller="GATK",
            variant_db_num=0,
            variant_db_hetero_num=0,
            variant_db_homo_num=0,
            artifact_db_num=5,  # High artifact count
        )

        mock_uow.variants.get_by_coordinates = AsyncMock(return_value=None)
        mock_uow.variants.save = AsyncMock()
        mock_uow.artifacts.get_by_coordinates = AsyncMock(return_value=None)
        mock_uow.artifacts.save = AsyncMock()

        stats = await loader.load_raw_variants(
            raw_variants=[raw_variant],
            sample_id=uuid4(),
            patient_id=uuid4(),
        )

        assert stats["new_artifacts"] == 1
        mock_uow.artifacts.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_variant_updates_existing_artifact(
        self,
        loader: VariantLoader,
        mock_uow: MagicMock,
        sample_artifact: GermlineArtifact,
    ) -> None:
        """Test loading variant updates existing artifact."""
        raw_variant = RawVariant(
            id=uuid4(),
            sample_id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            genotype="0/1",
            depth=100,
            variant_caller="GATK",
            variant_db_num=0,
            variant_db_hetero_num=0,
            variant_db_homo_num=0,
            artifact_db_num=3,
        )

        mock_uow.variants.get_by_coordinates = AsyncMock(return_value=None)
        mock_uow.variants.save = AsyncMock()
        mock_uow.artifacts.get_by_coordinates = AsyncMock(return_value=sample_artifact)
        mock_uow.artifacts.increment_occurrence = AsyncMock()

        stats = await loader.load_raw_variants(
            raw_variants=[raw_variant],
            sample_id=uuid4(),
            patient_id=uuid4(),
        )

        assert stats["updated_artifacts"] == 1
        mock_uow.artifacts.increment_occurrence.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_variants_error_handling(
        self,
        loader: VariantLoader,
        mock_uow: MagicMock,
        raw_variant: RawVariant,
    ) -> None:
        """Test error handling during variant loading."""
        mock_uow.variants.get_by_coordinates = AsyncMock(side_effect=Exception("Database error"))

        stats = await loader.load_raw_variants(
            raw_variants=[raw_variant],
            sample_id=uuid4(),
            patient_id=uuid4(),
        )

        assert stats["errors"] == 1
