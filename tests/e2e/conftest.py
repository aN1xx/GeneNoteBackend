"""E2E test fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.entities import (
    Patient,
    Sample,
    SampleCoverage,
    SampleVariant,
    User,
)
from src.domain.enums import SampleStatus, Sex, UserRole
from src.main import app
from src.presentation.dependencies.auth import get_current_user, get_unit_of_work


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def laborant_user() -> User:
    """Create laborant user."""
    return User(
        id=uuid4(),
        email="laborant@test.local",
        hashed_password="$2b$12$hashed_password",
        role=UserRole.LABORANT,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def geneticist_user() -> User:
    """Create geneticist user."""
    return User(
        id=uuid4(),
        email="geneticist@test.local",
        hashed_password="$2b$12$hashed_password",
        role=UserRole.GENETICIST,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def test_patient(laborant_user: User) -> Patient:
    """Create test patient."""
    return Patient(
        id=uuid4(),
        name="Иванов Иван Иванович",
        sex=Sex.MALE,
        birth_date=datetime(1990, 1, 15).date(),
        request_id="GN-2024-001",
        analysis_name="Полный экзом",
        analysis_date=datetime.now(UTC).date(),
    )


@pytest.fixture
def test_sample(test_patient: Patient, laborant_user: User) -> Sample:
    """Create test sample."""
    return Sample(
        id=uuid4(),
        patient_id=test_patient.id,
        sample_code="GN-2024-001",
        status=SampleStatus.AWAITING_ANNOTATION,
        uploaded_at=datetime.now(UTC),
        uploaded_by_id=laborant_user.id,
        fastq_r1_path="/data/GN-2024-001_R1.fastq.gz",
        fastq_r2_path="/data/GN-2024-001_R2.fastq.gz",
    )


@pytest.fixture
def test_variants(test_sample: Sample) -> list[SampleVariant]:
    """Create test variants."""
    return [
        SampleVariant(
            id=uuid4(),
            sample_id=test_sample.id,
            chromosome="1",
            position=12345678,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type="missense",
            transcript="NM_007294.4",
            exon_intron="exon 5",
            hgvs="c.123A>G",
            depth=100,
            genotype="0/1",
            variant_caller="GATK",
            variant_db_num=5,
            variant_db_hetero_num=3,
            variant_db_homo_num=2,
            artifact_db_num=0,
            pop_freq_gnomad=Decimal("0.001"),
        ),
        SampleVariant(
            id=uuid4(),
            sample_id=test_sample.id,
            chromosome="17",
            position=87654321,
            ref="C",
            alt="T",
            gene="TP53",
            variant_type="nonsense",
            transcript="NM_000546.6",
            exon_intron="exon 7",
            hgvs="c.456C>T",
            depth=150,
            genotype="0/1",
            variant_caller="GATK",
            variant_db_num=2,
            variant_db_hetero_num=2,
            variant_db_homo_num=0,
            artifact_db_num=1,
            pop_freq_gnomad=Decimal("0.0001"),
        ),
    ]


@pytest.fixture
def test_coverage(test_sample: Sample) -> SampleCoverage:
    """Create test coverage."""
    return SampleCoverage(
        id=uuid4(),
        sample_id=test_sample.id,
        depth_0x=Decimal("99.87"),
        depth_5x=Decimal("98.45"),
        depth_30x=Decimal("92.31"),
        depth_50x=Decimal("85.67"),
        depth_100x=Decimal("65.23"),
    )


@pytest.fixture
def mock_uow(
    test_patient: Patient,
    test_sample: Sample,
    test_variants: list[SampleVariant],
    test_coverage: SampleCoverage,
) -> MagicMock:
    """Create mock Unit of Work with sample data."""
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    # Mock patients repository
    uow.patients = MagicMock()
    uow.patients.get_by_id = AsyncMock(return_value=test_patient)
    uow.patients.get_by_request_id = AsyncMock(return_value=None)
    uow.patients.request_id_exists = AsyncMock(return_value=False)
    uow.patients.save = AsyncMock()

    # Mock samples repository
    uow.samples = MagicMock()
    uow.samples.get_by_id = AsyncMock(return_value=test_sample)
    uow.samples.save = AsyncMock()

    # Mock sample_variants repository
    uow.sample_variants = MagicMock()
    uow.sample_variants.get_by_sample_id = AsyncMock(return_value=test_variants)
    uow.sample_variants.get_by_id = AsyncMock(return_value=test_variants[0])
    uow.sample_variants.get_confirmed_variants = AsyncMock(return_value=[])
    uow.sample_variants.get_unannotated_by_sample = AsyncMock(return_value=test_variants)
    uow.sample_variants.count_by_sample = AsyncMock(return_value=len(test_variants))
    uow.sample_variants.count_annotated_by_sample = AsyncMock(return_value=0)
    uow.sample_variants.save = AsyncMock()

    # Mock sample_coverages repository
    uow.sample_coverages = MagicMock()
    uow.sample_coverages.get_by_sample_id = AsyncMock(return_value=test_coverage)

    # Mock pipelines repository
    uow.pipelines = MagicMock()
    uow.pipelines.save = AsyncMock()
    uow.pipelines.has_active_pipeline = AsyncMock(return_value=False)

    # Mock artifacts repository
    uow.artifacts = MagicMock()
    uow.artifacts.save = AsyncMock()
    uow.artifacts.get_by_coordinates = AsyncMock(return_value=None)
    uow.artifacts.artifact_exists = AsyncMock(return_value=False)

    return uow


@pytest.fixture
async def laborant_client(
    mock_uow: MagicMock,
    laborant_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with laborant user."""
    app.dependency_overrides[get_current_user] = lambda: laborant_user
    app.dependency_overrides[get_unit_of_work] = lambda: mock_uow

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def geneticist_client(
    mock_uow: MagicMock,
    geneticist_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with geneticist user."""
    app.dependency_overrides[get_current_user] = lambda: geneticist_user
    app.dependency_overrides[get_unit_of_work] = lambda: mock_uow

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
