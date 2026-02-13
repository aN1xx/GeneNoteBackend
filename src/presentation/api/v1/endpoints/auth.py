"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.application.dto.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.application.use_cases.auth import (
    LoginUseCase,
    RefreshTokenUseCase,
    RegisterUseCase,
)
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.infrastructure.security import JWTService, PasswordService
from src.presentation.dependencies import CurrentUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_login_use_case() -> LoginUseCase:
    """Get login use case instance."""
    return LoginUseCase(
        uow=SQLAlchemyUnitOfWork(async_session_factory),
        password_service=PasswordService(),
        jwt_service=JWTService(),
    )


def get_register_use_case() -> RegisterUseCase:
    """Get register use case instance."""
    return RegisterUseCase(
        uow=SQLAlchemyUnitOfWork(async_session_factory),
        password_service=PasswordService(),
    )


def get_refresh_token_use_case() -> RefreshTokenUseCase:
    """Get refresh token use case instance."""
    return RefreshTokenUseCase(
        uow=SQLAlchemyUnitOfWork(async_session_factory),
        jwt_service=JWTService(),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and return JWT tokens",
)
async def login(
    request: LoginRequest,
    use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
) -> TokenResponse:
    """Authenticate user with email and password."""
    return await use_case.execute(request)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account",
)
async def register(
    request: RegisterRequest,
    use_case: Annotated[RegisterUseCase, Depends(get_register_use_case)],
) -> UserResponse:
    """Register a new user."""
    return await use_case.execute(request)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Get new access token using refresh token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    use_case: Annotated[RefreshTokenUseCase, Depends(get_refresh_token_use_case)],
) -> TokenResponse:
    """Refresh access token using refresh token."""
    return await use_case.execute(request)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get information about the authenticated user",
)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
    )
