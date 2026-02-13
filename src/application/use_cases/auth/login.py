"""Login use case."""

from dataclasses import dataclass

from src.application.dto.auth import LoginRequest, TokenResponse
from src.domain.exceptions import InvalidCredentialsError, UserInactiveError
from src.domain.repositories import IUnitOfWork
from src.infrastructure.security import JWTService, PasswordService


@dataclass
class LoginUseCase:
    """Use case for user login."""

    uow: IUnitOfWork
    password_service: PasswordService
    jwt_service: JWTService

    async def execute(self, request: LoginRequest) -> TokenResponse:
        """Execute login use case.

        Args:
            request: Login request with email and password

        Returns:
            Token response with access and refresh tokens

        Raises:
            InvalidCredentialsError: If email or password is incorrect
            UserInactiveError: If user account is deactivated
        """
        async with self.uow:
            user = await self.uow.users.get_by_email(request.email)

            if not user:
                raise InvalidCredentialsError()

            if not self.password_service.verify(request.password, user.hashed_password):
                raise InvalidCredentialsError()

            if not user.is_active:
                raise UserInactiveError()

            access_token, refresh_token = self.jwt_service.create_token_pair(
                user_id=user.id,
                email=user.email,
                role=user.role,
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
            )
