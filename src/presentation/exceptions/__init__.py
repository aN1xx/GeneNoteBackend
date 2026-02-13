"""Presentation layer exception handling."""

from src.presentation.exceptions.handlers import (
    ErrorResponse,
    register_exception_handlers,
)

__all__ = [
    "ErrorResponse",
    "register_exception_handlers",
]
