from typing import Any
from uuid import UUID

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request
from wtforms import PasswordField, validators

from src.config import settings
from src.domain.enums import UserRole
from src.infrastructure.database.models.user import UserModel
from src.infrastructure.database.session import async_session_factory, engine
from src.infrastructure.security import JWTService
from src.infrastructure.security.password_service import password_service


class JWTAdminAuth(AuthenticationBackend):
    def __init__(self, jwt_service: JWTService) -> None:
        super().__init__(secret_key=settings.jwt_secret_key)
        self._jwt_service = jwt_service

    async def authenticate(self, request: Request) -> bool:
        token = self._extract_token(request)
        if token and await self._validate_token(token, request):
            return True

        user_id = request.session.get("user_id")
        if not user_id:
            return False

        async with async_session_factory() as session:
            user = await session.get(UserModel, UUID(user_id))
            if not user or not user.is_active or user.role != UserRole.ADMIN:
                return False
        return True

    async def login(self, request: Request) -> bool:
        form = await request.form()

        token = form.get("token")
        if token and isinstance(token, str):
            return await self._validate_token(token, request)

        email = form.get("email") or form.get("username")
        password = form.get("password")
        if not email or not password:
            return False

        if not isinstance(email, str) or not isinstance(password, str):
            return False

        async with async_session_factory() as session:
            stmt = select(UserModel).where(UserModel.email == email.lower())
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if (
                not user
                or not user.is_active
                or user.role != UserRole.ADMIN
                or not password_service.verify(password, user.hashed_password)
            ):
                return False

            request.session["user_id"] = str(user.id)
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    def _extract_token(self, request: Request) -> str | None:
        header = request.headers.get("Authorization")
        if header and header.startswith("Bearer "):
            return header.split(" ", 1)[1]
        return request.session.get("token")

    async def _validate_token(self, token: str, request: Request) -> bool:
        payload = self._jwt_service.verify_access_token(token)
        if not payload:
            return False

        async with async_session_factory() as session:
            user = await session.get(UserModel, UUID(payload.sub))

            if not user or not user.is_active or user.role != UserRole.ADMIN:
                return False

        request.session["token"] = token
        request.session["user_id"] = str(user.id)
        return True


class UserAdmin(ModelView, model=UserModel):
    column_list = [
        UserModel.id,
        UserModel.email,
        UserModel.role,
        UserModel.is_active,
        UserModel.created_at,
        UserModel.updated_at,
    ]
    column_searchable_list = [UserModel.email]
    column_filters = [UserModel.role, UserModel.is_active]
    can_create = True
    can_edit = True
    can_delete = True

    # Exclude internal fields from the form
    form_excluded_columns = ["id", "hashed_password", "created_at", "updated_at"]

    async def scaffold_form(self) -> type:
        """Override to add password field to the form."""
        form_class = await super().scaffold_form()

        # Add password field
        form_class.password = PasswordField(
            "Password",
            validators=[validators.Optional(), validators.Length(min=8)],
            description="Leave empty to keep current password (for edit)",
        )

        return form_class

    async def insert_model(self, request: Request, data: dict[str, Any]) -> UserModel:
        """Create user with hashed password."""
        password = data.pop("password", None)
        if not password:
            raise ValueError("Password is required for new users")

        # Hash password and add to data
        data["hashed_password"] = password_service.hash(password)

        # Call parent insert_model
        return await super().insert_model(request, data)

    async def update_model(self, request: Request, pk: Any, data: dict[str, Any]) -> UserModel:
        """Update user, optionally changing password."""
        password = data.pop("password", None)

        # If password provided, hash it
        if password:
            data["hashed_password"] = password_service.hash(password)

        # Call parent update_model
        return await super().update_model(request, pk, data)


def init_admin(app: FastAPI) -> Admin:
    auth_backend = JWTAdminAuth(jwt_service=JWTService())
    admin = Admin(
        app,
        engine,
        base_url="/admin",
        authentication_backend=auth_backend,
    )
    admin.add_view(UserAdmin)
    return admin
