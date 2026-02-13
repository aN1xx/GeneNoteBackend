"""Integration tests for variants API endpoints."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.dto.variant import VariantListResponse, VariantResponse
from src.domain.entities import GermlineVariant, User
from src.domain.enums import ACMGClassification, UserRole, VariantType
from src.domain.exceptions import VariantNotFoundError
from src.main import app
from src.presentation.dependencies.auth import get_current_user


class TestVariantsAPI:
    """Tests for variants endpoints."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create mock authenticated user."""
        return User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.GENETICIST,
            is_active=True,
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_variant(self) -> GermlineVariant:
        """Create sample variant."""
        now = datetime.now(UTC)
        return GermlineVariant(
            id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            exon_intron="exon 10",
            hgvs="c.1234A>G",
            acmg_classification=ACMGClassification.VUS,
            hetero_num=5,
            homo_num=2,
            sample_num=7,
            created_at=now,
            updated_at=now,
        )

    def _create_variant_response(self, variant: GermlineVariant) -> VariantResponse:
        """Create VariantResponse from GermlineVariant entity."""
        return VariantResponse(
            id=variant.id,
            chromosome=variant.chromosome,
            position=variant.position,
            ref=variant.ref,
            alt=variant.alt,
            gene=variant.gene,
            variant_name=variant.variant_name,
            variant_type=variant.variant_type,
            transcript=variant.transcript,
            exon_intron=variant.exon_intron,
            hgvs=variant.hgvs,
            hetero_num=variant.hetero_num,
            homo_num=variant.homo_num,
            sample_num=variant.sample_num,
            frequency=Decimal(str(variant.frequency)),
            pop_freq_gnomad=variant.pop_freq_gnomad,
            acmg_classification=variant.acmg_classification,
            is_pathogenic=variant.is_pathogenic(),
            created_at=variant.created_at,
            updated_at=variant.updated_at,
        )

    @pytest.mark.asyncio
    async def test_search_variants_success(
        self,
        mock_user: User,
        sample_variant: GermlineVariant,
    ) -> None:
        """Test searching variants."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.variants.SearchVariantsUseCase"
        ) as mock_search_cls:
            mock_search = mock_search_cls.return_value
            mock_search.execute = AsyncMock(
                return_value=VariantListResponse(
                    items=[self._create_variant_response(sample_variant)],
                    total=1,
                    limit=50,
                    offset=0,
                )
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get("/api/v1/variants?gene=BRCA1")

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_variant_success(
        self,
        mock_user: User,
        sample_variant: GermlineVariant,
    ) -> None:
        """Test getting variant by ID."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("src.presentation.api.v1.endpoints.variants.GetVariantUseCase") as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(return_value=self._create_variant_response(sample_variant))

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(f"/api/v1/variants/{sample_variant.id}")

                assert response.status_code == 200
                data = response.json()
                assert data["gene"] == "BRCA1"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_variant_not_found(
        self,
        mock_user: User,
    ) -> None:
        """Test getting non-existent variant."""
        variant_id = uuid4()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("src.presentation.api.v1.endpoints.variants.GetVariantUseCase") as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(side_effect=VariantNotFoundError(str(variant_id)))

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(f"/api/v1/variants/{variant_id}")

                assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_pathogenic_variants(
        self,
        mock_user: User,
        sample_variant: GermlineVariant,
    ) -> None:
        """Test getting pathogenic variants."""
        sample_variant.acmg_classification = ACMGClassification.PATHOGENIC
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.variants.GetPathogenicVariantsUseCase"
        ) as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(
                return_value=VariantListResponse(
                    items=[self._create_variant_response(sample_variant)],
                    total=1,
                    limit=100,
                    offset=0,
                )
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get("/api/v1/variants/pathogenic")

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_variant_by_name(
        self,
        mock_user: User,
        sample_variant: GermlineVariant,
    ) -> None:
        """Test getting variant by name."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.variants.GetVariantByNameUseCase"
        ) as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(return_value=self._create_variant_response(sample_variant))

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get("/api/v1/variants/by-name/1-12345-A-G")

                assert response.status_code == 200
                data = response.json()
                assert data["chromosome"] == "1"
            finally:
                app.dependency_overrides.clear()
