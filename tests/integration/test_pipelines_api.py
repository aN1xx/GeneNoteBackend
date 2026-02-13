"""Integration tests for pipelines API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.dto.pipeline import PipelineRunListResponse, PipelineRunResponse
from src.domain.entities import PipelineRun, User
from src.domain.enums import PipelineStatus, PipelineType, UserRole
from src.domain.exceptions import PipelineRunNotFoundError
from src.main import app
from src.presentation.dependencies.auth import get_current_user


class TestPipelinesAPI:
    """Tests for pipelines endpoints."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create mock authenticated user."""
        return User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.LABORANT,
            is_active=True,
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_pipeline_run(self) -> PipelineRun:
        """Create sample pipeline run."""
        return PipelineRun(
            id=uuid4(),
            sample_id=uuid4(),
            pipeline_type=PipelineType.VARIANT_CALLING,
            status=PipelineStatus.QUEUED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    def _create_pipeline_response(self, run: PipelineRun) -> PipelineRunResponse:
        """Create PipelineRunResponse from PipelineRun entity."""
        return PipelineRunResponse(
            id=run.id,
            sample_id=run.sample_id,
            pipeline_type=run.pipeline_type,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            output_path=run.output_path,
            error_message=run.error_message,
            progress_percent=run.progress_percent or 0,
            duration_seconds=run.duration_seconds,
            is_terminal=run.is_terminal,
            is_active=run.is_active,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @pytest.mark.asyncio
    async def test_start_pipeline_success(
        self,
        mock_user: User,
        sample_pipeline_run: PipelineRun,
    ) -> None:
        """Test starting pipeline successfully."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with (
            patch(
                "src.presentation.api.v1.endpoints.pipelines.StartPipelineUseCase"
            ) as mock_start_cls,
            patch("src.presentation.api.v1.endpoints.pipelines.get_kafka_producer") as mock_kafka,
        ):
            mock_kafka.return_value = MagicMock()
            mock_start = mock_start_cls.return_value
            mock_start.execute = AsyncMock(
                return_value=self._create_pipeline_response(sample_pipeline_run)
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/pipelines/start",
                        json={
                            "sample_id": str(sample_pipeline_run.sample_id),
                            "pipeline_type": "variant_calling",
                        },
                    )

                assert response.status_code == 201
                data = response.json()
                assert data["pipeline_type"] == "variant_calling"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_pipeline_run_success(
        self,
        mock_user: User,
        sample_pipeline_run: PipelineRun,
    ) -> None:
        """Test getting pipeline run by ID."""
        sample_pipeline_run.status = PipelineStatus.RUNNING
        sample_pipeline_run.started_at = datetime.utcnow()
        sample_pipeline_run.progress_percent = 50

        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.pipelines.GetPipelineRunUseCase"
        ) as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(
                return_value=self._create_pipeline_response(sample_pipeline_run)
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(f"/api/v1/pipelines/{sample_pipeline_run.id}")

                assert response.status_code == 200
                data = response.json()
                assert data["progress_percent"] == 50
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cancel_pipeline_success(
        self,
        mock_user: User,
        sample_pipeline_run: PipelineRun,
    ) -> None:
        """Test cancelling pipeline."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        # Mock UoW for the cancel endpoint (which has inline logic)
        mock_uow = MagicMock()
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)
        mock_uow.commit = AsyncMock()
        mock_uow.pipelines = MagicMock()

        # Set up the pipeline run to be cancelled - use QUEUED status which can be cancelled
        sample_pipeline_run.status = PipelineStatus.QUEUED
        sample_pipeline_run.started_at = datetime.utcnow()
        mock_uow.pipelines.get_by_id = AsyncMock(return_value=sample_pipeline_run)
        mock_uow.pipelines.save = AsyncMock()

        with patch(
            "src.presentation.api.v1.endpoints.pipelines.get_uow",
            return_value=mock_uow,
        ):
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(f"/api/v1/pipelines/{sample_pipeline_run.id}/cancel")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "cancelled"
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_pipeline_not_found(
        self,
        mock_user: User,
    ) -> None:
        """Test getting non-existent pipeline."""
        pipeline_id = uuid4()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.pipelines.GetPipelineRunUseCase"
        ) as mock_get_cls:
            mock_get = mock_get_cls.return_value
            mock_get.execute = AsyncMock(side_effect=PipelineRunNotFoundError(str(pipeline_id)))

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(f"/api/v1/pipelines/{pipeline_id}")

                assert response.status_code == 404
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_pipelines_by_sample(
        self,
        mock_user: User,
        sample_pipeline_run: PipelineRun,
    ) -> None:
        """Test listing pipelines by sample."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch(
            "src.presentation.api.v1.endpoints.pipelines.GetPipelineRunsBySampleUseCase"
        ) as mock_list_cls:
            mock_list = mock_list_cls.return_value
            mock_list.execute = AsyncMock(
                return_value=PipelineRunListResponse(
                    items=[self._create_pipeline_response(sample_pipeline_run)],
                    total=1,
                    limit=100,
                    offset=0,
                )
            )

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.get(
                        f"/api/v1/pipelines/by-sample/{sample_pipeline_run.sample_id}"
                    )

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
                assert len(data["items"]) >= 1
            finally:
                app.dependency_overrides.clear()
