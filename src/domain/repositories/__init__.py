"""Domain repository interfaces."""

from src.domain.repositories.artifact_repository import IArtifactRepository
from src.domain.repositories.base import IRepository
from src.domain.repositories.file_record_repository import IFileRecordRepository
from src.domain.repositories.patient_repository import IPatientRepository
from src.domain.repositories.pipeline_repository import IPipelineRepository
from src.domain.repositories.sample_coverage_repository import ISampleCoverageRepository
from src.domain.repositories.sample_repository import ISampleRepository
from src.domain.repositories.sample_variant_repository import ISampleVariantRepository
from src.domain.repositories.unit_of_work import IUnitOfWork
from src.domain.repositories.user_repository import IUserRepository
from src.domain.repositories.variant_repository import IVariantRepository

__all__ = [
    "IArtifactRepository",
    "IFileRecordRepository",
    "IPatientRepository",
    "IPipelineRepository",
    "IRepository",
    "ISampleCoverageRepository",
    "ISampleRepository",
    "ISampleVariantRepository",
    "IUnitOfWork",
    "IUserRepository",
    "IVariantRepository",
]
