"""SQLAlchemy Unit of Work implementation."""

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.repositories import IUnitOfWork
from src.infrastructure.database.repositories import (
    SQLAlchemyArtifactRepository,
    SQLAlchemyFileRecordRepository,
    SQLAlchemyPatientRepository,
    SQLAlchemyPipelineRepository,
    SQLAlchemySampleCoverageRepository,
    SQLAlchemySampleRepository,
    SQLAlchemySampleVariantRepository,
    SQLAlchemyUserRepository,
    SQLAlchemyVariantRepository,
)


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """SQLAlchemy implementation of Unit of Work pattern."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize Unit of Work with session factory.

        Args:
            session_factory: Async session factory for creating sessions
        """
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        """Enter async context manager, create session and repositories."""
        self._session = self._session_factory()
        self.users = SQLAlchemyUserRepository(self._session)
        self.patients = SQLAlchemyPatientRepository(self._session)
        self.samples = SQLAlchemySampleRepository(self._session)
        self.sample_variants = SQLAlchemySampleVariantRepository(self._session)
        self.sample_coverages = SQLAlchemySampleCoverageRepository(self._session)
        self.variants = SQLAlchemyVariantRepository(self._session)
        self.artifacts = SQLAlchemyArtifactRepository(self._session)
        self.pipelines = SQLAlchemyPipelineRepository(self._session)
        self.file_records = SQLAlchemyFileRecordRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager, rollback on exception and close session."""
        if exc_type is not None:
            await self.rollback()
        if self._session:
            await self._session.close()

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._session:
            await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._session:
            await self._session.rollback()
