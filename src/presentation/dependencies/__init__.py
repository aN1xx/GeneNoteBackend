"""FastAPI dependencies."""

from src.presentation.dependencies.auth import (
    AdminUser,
    CurrentActiveUser,
    CurrentUser,
    GeneticistUser,
    LaborantUser,
    RoleChecker,
    Token,
    get_current_active_user,
    get_current_user,
    get_jwt_service,
    get_token_payload,
    get_unit_of_work,
    require_admin,
    require_any_role,
    require_geneticist,
    require_laborant,
)

__all__ = [
    "AdminUser",
    "CurrentActiveUser",
    "CurrentUser",
    "GeneticistUser",
    "LaborantUser",
    "RoleChecker",
    "Token",
    "get_current_active_user",
    "get_current_user",
    "get_jwt_service",
    "get_token_payload",
    "get_unit_of_work",
    "require_admin",
    "require_any_role",
    "require_geneticist",
    "require_laborant",
]
