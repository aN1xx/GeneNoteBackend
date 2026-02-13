"""User SQLAlchemy model."""

from sqlalchemy import Boolean, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.enums import UserRole
from src.infrastructure.database.base import Base, TimestampMixin, UUIDMixin


class UserRoleType(TypeDecorator):
    """Custom type for UserRole enum that uses values instead of names."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Use PostgreSQL ENUM for PostgreSQL, String for others."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(
                ENUM("laborant", "geneticist", "admin", name="user_role", create_type=False)
            )
        return dialect.type_descriptor(String(50))

    def process_bind_param(self, value, dialect):
        """Convert enum to its value for database storage."""
        if value is None:
            return None
        if isinstance(value, UserRole):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        """Convert database value back to enum."""
        if value is None:
            return None
        if isinstance(value, str):
            return UserRole(value)
        return value


class UserModel(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for User entity."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        UserRoleType(),
        nullable=False,
        default=UserRole.LABORANT,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
