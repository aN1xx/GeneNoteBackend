"""Integration tests for patients API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.dto.patient import PatientListResponse, PatientResponse
from src.domain.entities import Patient, User
from src.domain.enums import Sex, UserRole
from src.domain.exceptions import PatientNotFoundError
from src.main import app
from src.presentation.dependencies.auth import get_current_user


class TestPatientsAPI:
    """Tests for patients endpoints."""

    @pytest.fixture
    def sample_patient(self) -> Patient:
        """Create sample patient."""
        return Patient(
            id=uuid4(),
            name="Test Patient",
            sex=Sex.MALE,
            birth_date=datetime(1990, 1, 15).date(),
            request_id="REQ-001",
            analysis_name="WES Analysis",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

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

    def _create_patient_response(self, patient: Patient) -> PatientResponse:
        """Create PatientResponse from Patient entity."""
        return PatientResponse(
            id=patient.id,
            name=patient.name,
            sex=patient.sex,
            birth_date=patient.birth_date,
            request_id=patient.request_id,
            analysis_name=patient.analysis_name,
            analysis_date=patient.analysis_date,
            age=patient.age,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
        )

    @pytest.mark.asyncio
    async def test_create_patient_success(
        self,
        mock_user: User,
        sample_patient: Patient,
    ) -> None:
        """Test successful patient creation."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.patients.CreatePatientUseCase"
        ) as mock_create_cls:
            mock_create = mock_create_cls.return_value
            mock_create.execute = AsyncMock(
                return_value=self._create_patient_response(sample_patient)
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/patients",
                        json={
                            "name": "Test Patient",
                            "sex": "м",
                            "birth_date": "1990-01-15",
                            "request_id": "REQ-001",
                            "analysis_name": "WES Analysis",
                        },
                    )

                assert response.status_code == 201
                data = response.json()
                assert data["name"] == "Test Patient"
                assert data["request_id"] == "REQ-001"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_patients_success(
        self,
        mock_user: User,
        sample_patient: Patient,
    ) -> None:
        """Test listing patients."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.patients.ListPatientsUseCase"
        ) as mock_list_cls:
            mock_list = mock_list_cls.return_value
            mock_list.execute = AsyncMock(
                return_value=PatientListResponse(
                    items=[self._create_patient_response(sample_patient)],
                    total=1,
                    limit=50,
                    offset=0,
                )
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get("/api/v1/patients")

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
                assert len(data["items"]) >= 1
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_patient_success(
        self,
        mock_user: User,
        sample_patient: Patient,
    ) -> None:
        """Test getting patient by ID."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("src.presentation.api.v1.endpoints.patients.GetPatientUseCase") as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(return_value=self._create_patient_response(sample_patient))

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(f"/api/v1/patients/{sample_patient.id}")

                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Test Patient"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_patient_not_found(
        self,
        mock_user: User,
    ) -> None:
        """Test getting non-existent patient."""
        patient_id = uuid4()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("src.presentation.api.v1.endpoints.patients.GetPatientUseCase") as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(side_effect=PatientNotFoundError(str(patient_id)))

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(f"/api/v1/patients/{patient_id}")

                assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_search_patients_success(
        self,
        mock_user: User,
        sample_patient: Patient,
    ) -> None:
        """Test searching patients."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.patients.SearchPatientsUseCase"
        ) as mock_search_cls:
            mock_search = mock_search_cls.return_value
            mock_search.execute = AsyncMock(
                return_value=PatientListResponse(
                    items=[self._create_patient_response(sample_patient)],
                    total=1,
                    limit=50,
                    offset=0,
                )
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get("/api/v1/patients/search?query=Test")

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_patients_unauthorized(self) -> None:
        """Test patients endpoints require authentication."""
        app.dependency_overrides.clear()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/patients")

        assert response.status_code == 401
