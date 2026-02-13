"""Integration tests for samples API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.dto.sample import SampleListResponse, SampleResponse
from src.domain.entities import Sample, User
from src.domain.enums import SampleStatus, UserRole
from src.domain.exceptions import SampleNotFoundError
from src.main import app
from src.presentation.dependencies.auth import get_current_user


class TestSamplesAPI:
    """Tests for samples endpoints."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create mock authenticated user."""
        return User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.LABORANT,
            is_active=True,
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def geneticist_user(self) -> User:
        """Create geneticist user."""
        return User(
            id=uuid4(),
            email="geneticist@example.com",
            hashed_password="hashed",
            role=UserRole.GENETICIST,
            is_active=True,
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_sample(self) -> Sample:
        """Create sample sample."""
        now = datetime.now(UTC)
        return Sample(
            id=uuid4(),
            patient_id=uuid4(),
            sample_code="SAMPLE-001",
            status=SampleStatus.UPLOADED,
            created_at=now,
            updated_at=now,
        )

    def _create_sample_response(self, sample: Sample) -> SampleResponse:
        """Create SampleResponse from Sample entity."""
        has_report = sample.report_path is not None
        is_resequencing_report = bool(sample.requires_resequencing) if has_report else None

        return SampleResponse(
            id=sample.id,
            patient_id=sample.patient_id,
            sample_code=sample.sample_code,
            status=sample.status,
            collection_date=sample.collection_date,
            fastq_r1_path=sample.fastq_r1_path,
            fastq_r2_path=sample.fastq_r2_path,
            tsv_patients_path=sample.tsv_patients_path,
            has_fastq_files=sample.has_fastq_files(),
            can_start_variant_calling=sample.can_start_variant_calling(),
            can_annotate=sample.can_annotate(),
            can_generate_report=sample.can_generate_report(),
            has_report=has_report,
            is_resequencing_report=is_resequencing_report,
            created_at=sample.created_at,
            updated_at=sample.updated_at,
        )

    @pytest.mark.asyncio
    async def test_create_sample_success(
        self,
        mock_user: User,
        sample_sample: Sample,
    ) -> None:
        """Test successful sample creation."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.samples.CreateSampleUseCase"
        ) as mock_create_cls:
            mock_create = mock_create_cls.return_value
            mock_create.execute = AsyncMock(
                return_value=self._create_sample_response(sample_sample)
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/samples",
                        json={
                            "patient_id": str(sample_sample.patient_id),
                            "sample_code": "SAMPLE-001",
                        },
                    )

                assert response.status_code == 201
                data = response.json()
                assert data["sample_code"] == "SAMPLE-001"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_sample_success(
        self,
        mock_user: User,
        sample_sample: Sample,
    ) -> None:
        """Test getting sample by ID."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("src.presentation.api.v1.endpoints.samples.GetSampleUseCase") as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(return_value=self._create_sample_response(sample_sample))

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(f"/api/v1/samples/{sample_sample.id}")

                assert response.status_code == 200
                data = response.json()
                assert data["sample_code"] == "SAMPLE-001"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_sample_not_found(
        self,
        mock_user: User,
    ) -> None:
        """Test getting non-existent sample."""
        sample_id = uuid4()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("src.presentation.api.v1.endpoints.samples.GetSampleUseCase") as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(side_effect=SampleNotFoundError(str(sample_id)))

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(f"/api/v1/samples/{sample_id}")

                assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_samples_awaiting_annotation(
        self,
        geneticist_user: User,
        sample_sample: Sample,
    ) -> None:
        """Test getting samples awaiting annotation."""
        sample_sample.status = SampleStatus.AWAITING_ANNOTATION
        app.dependency_overrides[get_current_user] = lambda: geneticist_user

        with patch(
            "src.presentation.api.v1.endpoints.samples.GetAwaitingAnnotationSamplesUseCase"
        ) as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(
                return_value=SampleListResponse(
                    items=[self._create_sample_response(sample_sample)],
                    total=1,
                    limit=100,
                    offset=0,
                )
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get("/api/v1/samples/awaiting-annotation")

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_samples_by_patient(
        self,
        mock_user: User,
        sample_sample: Sample,
    ) -> None:
        """Test getting samples by patient ID."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.samples.GetSamplesByPatientUseCase"
        ) as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(
                return_value=SampleListResponse(
                    items=[self._create_sample_response(sample_sample)],
                    total=1,
                    limit=100,
                    offset=0,
                )
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(
                        f"/api/v1/samples/by-patient/{sample_sample.patient_id}"
                    )

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
            finally:
                app.dependency_overrides.clear()
