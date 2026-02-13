"""Refresh token use case."""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.auth import RefreshTokenRequest, TokenResponse
from src.domain.exceptions import InvalidTokenError, UserInactiveError, UserNotFoundError
from src.domain.repositories import IUnitOfWork
from src.infrastructure.security import JWTService


@dataclass
class RefreshTokenUseCase:
    """Use case for refreshing access token."""

    uow: IUnitOfWork
    jwt_service: JWTService

    async def execute(self, request: RefreshTokenRequest) -> TokenResponse:
        """Execute refresh token use case.

        Args:
            request: Refresh token request

        Returns:
            New token pair

        Raises:
            InvalidTokenError: If refresh token is invalid or expired
            UserNotFoundError: If user no longer exists
            UserInactiveError: If user account is deactivated
        """
        payload = self.jwt_service.verify_refresh_token(request.refresh_token)

        if not payload:
            raise InvalidTokenError("Invalid or expired refresh token")

        async with self.uow:
            user = await self.uow.users.get_by_id(UUID(payload.sub))

            if not user:
                raise UserNotFoundError(payload.sub)

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
