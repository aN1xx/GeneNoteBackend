"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.domain.entities import (
    GermlineArtifact,
    GermlineVariant,
    Patient,
    RawVariant,
    Sample,
    User,
)
from src.domain.enums import (
    ACMGClassification,
    SampleStatus,
    Sex,
    UserRole,
    VariantType,
)
from src.domain.repositories import IUnitOfWork


# Event loop fixture
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Domain entity fixtures
@pytest.fixture
def sample_user() -> User:
    """Create a sample user for testing."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        role=UserRole.LABORANT,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_patient() -> Patient:
    """Create a sample patient for testing."""
    return Patient(
        id=uuid4(),
        name="Test Patient",
        sex=Sex.MALE,
        birth_date=datetime(1990, 1, 15).date(),
        request_id="REQ-001",
        analysis_name="WES Analysis",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_sample(sample_patient: Patient) -> Sample:
    """Create a sample for testing."""
    return Sample(
        id=uuid4(),
        patient_id=sample_patient.id,
        sample_code="SAMPLE-001",
        status=SampleStatus.UPLOADED,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_variant() -> GermlineVariant:
    """Create a sample variant for testing."""
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
    )


@pytest.fixture
def sample_raw_variant(sample_sample: Sample) -> RawVariant:
    """Create a raw variant for testing."""
    return RawVariant(
        id=uuid4(),
        sample_id=sample_sample.id,
        chromosome="1",
        position=12345,
        ref="A",
        alt="G",
        gene="BRCA1",
        variant_type=VariantType.SNV,
        transcript="NM_007294.4",
        exon_intron="exon 10",
        hgvs="c.1234A>G",
        genotype="гетерозигота",
        depth=100,
        variant_caller="gatk",
        gatk_depth=100,
        gatk_allele_depth=50,
        gatk_allele_fraction=Decimal("0.5"),
        variant_db_num=10,
        variant_db_hetero_num=7,
        variant_db_homo_num=3,
        artifact_db_num=0,
    )


@pytest.fixture
def sample_artifact() -> GermlineArtifact:
    """Create a sample artifact for testing."""
    return GermlineArtifact(
        id=uuid4(),
        chromosome="1",
        position=12345,
        ref="A",
        alt="G",
        occurrence_num=10,
        sample_num=5,
    )


# Mock fixtures
@pytest.fixture
def mock_uow() -> MagicMock:
    """Create a mock Unit of Work."""
    uow = MagicMock(spec=IUnitOfWork)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    # Mock repositories
    uow.users = MagicMock()
    uow.patients = MagicMock()
    uow.samples = MagicMock()
    uow.variants = MagicMock()
    uow.artifacts = MagicMock()
    uow.pipelines = MagicMock()

    return uow


@pytest.fixture
def mock_password_service() -> MagicMock:
    """Create a mock password service."""
    service = MagicMock()
    service.hash = MagicMock(return_value="hashed_password")
    service.verify = MagicMock(return_value=True)
    return service


@pytest.fixture
def mock_jwt_service() -> MagicMock:
    """Create a mock JWT service."""
    service = MagicMock()
    service.create_token_pair = MagicMock(return_value=("access_token", "refresh_token"))
    service.decode_token = MagicMock(return_value={"sub": "user_id", "email": "test@example.com"})
    return service


@pytest.fixture
def mock_kafka_producer() -> MagicMock:
    """Create a mock Kafka producer."""
    producer = MagicMock()
    producer.send_pipeline_event = AsyncMock()
    producer.send = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    return producer


# Configuration fixtures
@pytest.fixture
def test_config() -> dict[str, Any]:
    """Test configuration."""
    return {
        "database_url": "postgresql+asyncpg://test:test@localhost:5432/test_db",
        "jwt_secret": "test-secret-key-for-testing-only",
        "jwt_algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "refresh_token_expire_days": 7,
        "kafka_bootstrap_servers": "localhost:9092",
    }
