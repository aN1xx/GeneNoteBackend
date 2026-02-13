"""Global exception handlers for FastAPI."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.domain.exceptions import (
    BusinessRuleViolationError,
    DomainError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
)


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str
    detail: str
    code: str | None = None


def create_error_response(
    status_code: int,
    error: str,
    detail: str,
    code: str | None = None,
) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error, detail=detail, code=code).model_dump(exclude_none=True),
    )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle generic domain errors."""
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error="DomainError",
        detail=exc.message,
    )


async def entity_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    """Handle entity not found errors."""
    return create_error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        error="NotFound",
        detail=exc.message,
        code=f"{exc.entity_type.upper()}_NOT_FOUND",
    )


async def entity_already_exists_handler(
    request: Request, exc: EntityAlreadyExistsError
) -> JSONResponse:
    """Handle entity already exists errors."""
    return create_error_response(
        status_code=status.HTTP_409_CONFLICT,
        error="Conflict",
        detail=exc.message,
        code=f"{exc.entity_type.upper()}_ALREADY_EXISTS",
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors."""
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error="ValidationError",
        detail=exc.message,
        code="VALIDATION_ERROR",
    )


async def business_rule_violation_handler(
    request: Request, exc: BusinessRuleViolationError
) -> JSONResponse:
    """Handle business rule violations."""
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error="BusinessRuleViolation",
        detail=exc.message,
        code="BUSINESS_RULE_VIOLATION",
    )


async def unauthorized_error_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    """Handle unauthorized errors."""
    return create_error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        error="Unauthorized",
        detail=exc.message,
        code="UNAUTHORIZED",
    )


async def forbidden_error_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    """Handle forbidden errors."""
    return create_error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        error="Forbidden",
        detail=exc.message,
        code="FORBIDDEN",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Order matters - more specific exceptions first
    app.add_exception_handler(EntityNotFoundError, entity_not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(EntityAlreadyExistsError, entity_already_exists_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(BusinessRuleViolationError, business_rule_violation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UnauthorizedError, unauthorized_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ForbiddenError, forbidden_error_handler)  # type: ignore[arg-type]
    # Generic domain error handler last
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
