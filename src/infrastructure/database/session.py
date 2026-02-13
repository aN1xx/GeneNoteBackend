"""Database session configuration."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config import settings

# Create async engine
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.database_echo,
    poolclass=NullPool if settings.environment == "testing" else None,
    pool_size=settings.database_pool_size if settings.environment != "testing" else None,
    max_overflow=settings.database_max_overflow if settings.environment != "testing" else None,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
