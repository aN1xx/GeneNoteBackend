"""Unit of Work interface."""

from abc import ABC, abstractmethod
from types import TracebackType

from src.domain.repositories.artifact_repository import IArtifactRepository
from src.domain.repositories.file_record_repository import IFileRecordRepository
from src.domain.repositories.patient_repository import IPatientRepository
from src.domain.repositories.pipeline_repository import IPipelineRepository
from src.domain.repositories.sample_coverage_repository import ISampleCoverageRepository
from src.domain.repositories.sample_repository import ISampleRepository
from src.domain.repositories.sample_variant_repository import ISampleVariantRepository
from src.domain.repositories.user_repository import IUserRepository
from src.domain.repositories.variant_repository import IVariantRepository


class IUnitOfWork(ABC):
    """Unit of Work interface for managing transactions."""

    users: IUserRepository
    patients: IPatientRepository
    samples: ISampleRepository
    sample_variants: ISampleVariantRepository
    sample_coverages: ISampleCoverageRepository
    variants: IVariantRepository
    artifacts: IArtifactRepository
    pipelines: IPipelineRepository
    file_records: IFileRecordRepository

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork":
        """Enter async context manager."""
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...
