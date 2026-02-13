"""Register use case."""

from dataclasses import dataclass
from uuid import uuid4

from src.application.dto.auth import RegisterRequest, UserResponse
from src.domain.entities import User
from src.domain.exceptions import UserAlreadyExistsError
from src.domain.repositories import IUnitOfWork
from src.infrastructure.security import PasswordService


@dataclass
class RegisterUseCase:
    """Use case for user registration."""

    uow: IUnitOfWork
    password_service: PasswordService

    async def execute(self, request: RegisterRequest) -> UserResponse:
        """Execute registration use case.

        Args:
            request: Registration request with email, password, and role

        Returns:
            Created user response

        Raises:
            UserAlreadyExistsError: If email is already registered
        """
        async with self.uow:
            if await self.uow.users.email_exists(request.email):
                raise UserAlreadyExistsError(request.email)

            hashed_password = self.password_service.hash(request.password)

            user = User(
                id=uuid4(),
                email=request.email,
                hashed_password=hashed_password,
                role=request.role,
                is_active=True,
            )

            saved_user = await self.uow.users.save(user)
            await self.uow.commit()

            return UserResponse(
                id=saved_user.id,
                email=saved_user.email,
                role=saved_user.role,
                is_active=saved_user.is_active,
            )
