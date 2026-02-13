"""Tests for auth use cases."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dto import LoginRequest, RegisterRequest, TokenResponse
from src.application.use_cases.auth import LoginUseCase, RegisterUseCase
from src.domain.entities import User
from src.domain.enums import UserRole
from src.domain.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)


class TestLoginUseCase:
    """Tests for LoginUseCase."""

    @pytest.fixture
    def login_use_case(
        self,
        mock_uow: MagicMock,
        mock_password_service: MagicMock,
        mock_jwt_service: MagicMock,
    ) -> LoginUseCase:
        """Create login use case with mocked dependencies."""
        return LoginUseCase(
            uow=mock_uow,
            password_service=mock_password_service,
            jwt_service=mock_jwt_service,
        )

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        login_use_case: LoginUseCase,
        mock_uow: MagicMock,
        mock_password_service: MagicMock,
        mock_jwt_service: MagicMock,
        sample_user: User,
    ) -> None:
        """Test successful login."""
        mock_uow.users.get_by_email = AsyncMock(return_value=sample_user)
        mock_password_service.verify.return_value = True
        mock_jwt_service.create_token_pair.return_value = ("access_token", "refresh_token")

        request = LoginRequest(
            email="test@example.com",
            password="password123",
        )
        result = await login_use_case.execute(request)

        assert isinstance(result, TokenResponse)
        assert result.access_token == "access_token"
        assert result.refresh_token == "refresh_token"

    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self,
        login_use_case: LoginUseCase,
        mock_uow: MagicMock,
    ) -> None:
        """Test login with non-existent user."""
        mock_uow.users.get_by_email = AsyncMock(return_value=None)

        request = LoginRequest(
            email="nonexistent@example.com",
            password="password123",
        )

        with pytest.raises(InvalidCredentialsError):
            await login_use_case.execute(request)

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        login_use_case: LoginUseCase,
        mock_uow: MagicMock,
        mock_password_service: MagicMock,
        sample_user: User,
    ) -> None:
        """Test login with wrong password."""
        mock_uow.users.get_by_email = AsyncMock(return_value=sample_user)
        mock_password_service.verify.return_value = False

        request = LoginRequest(
            email="test@example.com",
            password="wrong_password",
        )

        with pytest.raises(InvalidCredentialsError):
            await login_use_case.execute(request)


class TestRegisterUseCase:
    """Tests for RegisterUseCase."""

    @pytest.fixture
    def register_use_case(
        self,
        mock_uow: MagicMock,
        mock_password_service: MagicMock,
    ) -> RegisterUseCase:
        """Create register use case with mocked dependencies."""
        return RegisterUseCase(
            uow=mock_uow,
            password_service=mock_password_service,
        )

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        register_use_case: RegisterUseCase,
        mock_uow: MagicMock,
        mock_password_service: MagicMock,
    ) -> None:
        """Test successful registration."""
        mock_uow.users.email_exists = AsyncMock(return_value=False)
        mock_uow.users.save = AsyncMock(side_effect=lambda user: user)
        mock_password_service.hash.return_value = "hashed_password"

        request = RegisterRequest(
            email="new@example.com",
            password="password123",
            role=UserRole.LABORANT,
        )
        result = await register_use_case.execute(request)

        assert result.email == "new@example.com"
        mock_uow.users.save.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_exists(
        self,
        register_use_case: RegisterUseCase,
        mock_uow: MagicMock,
    ) -> None:
        """Test registration with existing email."""
        mock_uow.users.email_exists = AsyncMock(return_value=True)

        request = RegisterRequest(
            email="test@example.com",
            password="password123",
            role=UserRole.LABORANT,
        )

        with pytest.raises(UserAlreadyExistsError):
            await register_use_case.execute(request)
