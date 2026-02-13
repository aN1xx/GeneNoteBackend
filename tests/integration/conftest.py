"""Integration test fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.entities import User
from src.domain.enums import UserRole
from src.main import app
from src.presentation.dependencies.auth import (
    get_current_user,
    get_unit_of_work,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_uow():
    """Create mock Unit of Work for integration tests."""
    uow = MagicMock()
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
def test_user() -> User:
    """Create test user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$hashed_password",
        role=UserRole.LABORANT,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def admin_user() -> User:
    """Create admin user."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="$2b$12$hashed_password",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def geneticist_user() -> User:
    """Create geneticist user."""
    return User(
        id=uuid4(),
        email="geneticist@example.com",
        hashed_password="$2b$12$hashed_password",
        role=UserRole.GENETICIST,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_jwt_payload(test_user: User) -> dict[str, Any]:
    """Create mock JWT payload."""
    return {
        "sub": str(test_user.id),
        "email": test_user.email,
        "role": test_user.role.value,
        "type": "access",
        "exp": datetime.now(UTC).timestamp() + 3600,
    }


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create authorization headers with mock token."""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
async def client(
    mock_uow: MagicMock,
    test_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with mocked dependencies."""
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
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
async def admin_client(
    mock_uow: MagicMock,
    admin_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with admin user."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
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
async def unauthenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client without authentication."""
    # Clear any existing overrides
    app.dependency_overrides.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac
