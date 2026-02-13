"""Authentication DTOs."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.domain.enums import UserRole


class LoginRequest(BaseModel):
    """Login request DTO."""

    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class RegisterRequest(BaseModel):
    """User registration request DTO."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.LABORANT


class TokenResponse(BaseModel):
    """Token response DTO."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request DTO."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response DTO."""

    id: UUID
    email: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Change password request DTO."""

    current_password: str
    new_password: str = Field(min_length=8)


class UpdateUserRequest(BaseModel):
    """Update user request DTO (admin only)."""

    role: UserRole | None = None
    is_active: bool | None = None
