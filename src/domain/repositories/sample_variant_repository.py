"""Sample variant repository interface."""

from abc import abstractmethod
from uuid import UUID

from src.domain.entities import SampleVariant
from src.domain.repositories.base import IRepository


class ISampleVariantRepository(IRepository[SampleVariant]):
    """Repository interface for sample variants."""

    @abstractmethod
    async def get_by_sample_id(
        self,
        sample_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SampleVariant]:
        """Get all variants for a sample.

        Args:
            sample_id: Sample UUID
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of sample variants
        """
        ...

    @abstractmethod
    async def get_unannotated_by_sample(
        self,
        sample_id: UUID,
    ) -> list[SampleVariant]:
        """Get unannotated variants for a sample.

        Args:
            sample_id: Sample UUID

        Returns:
            List of unannotated variants
        """
        ...

    @abstractmethod
    async def get_by_coordinates(
        self,
        sample_id: UUID,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> SampleVariant | None:
        """Get variant by genomic coordinates within a sample.

        Args:
            sample_id: Sample UUID
            chromosome: Chromosome (e.g., '1', 'X')
            position: Genomic position
            ref: Reference allele
            alt: Alternate allele

        Returns:
            SampleVariant if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_confirmed_variants(
        self,
        sample_id: UUID,
    ) -> list[SampleVariant]:
        """Get variants confirmed as true variants (is_variant=True).

        Args:
            sample_id: Sample UUID

        Returns:
            List of confirmed variants
        """
        ...

    @abstractmethod
    async def get_artifacts(
        self,
        sample_id: UUID,
    ) -> list[SampleVariant]:
        """Get variants marked as artifacts (is_artifact=True).

        Args:
            sample_id: Sample UUID

        Returns:
            List of artifacts
        """
        ...

    @abstractmethod
    async def get_annotated_variants(
        self,
        sample_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SampleVariant]:
        """Get all annotated variants (both confirmed variants and artifacts).

        Args:
            sample_id: Sample UUID
            limit: Maximum number of variants to return
            offset: Number of variants to skip

        Returns:
            List of annotated variants
        """
        ...

    @abstractmethod
    async def save_many(
        self,
        variants: list[SampleVariant],
    ) -> list[SampleVariant]:
        """Save multiple variants in bulk.

        Args:
            variants: List of variants to save

        Returns:
            List of saved variants
        """
        ...

    @abstractmethod
    async def count_by_sample(self, sample_id: UUID) -> int:
        """Count variants for a sample.

        Args:
            sample_id: Sample UUID

        Returns:
            Number of variants
        """
        ...

    @abstractmethod
    async def count_annotated_by_sample(self, sample_id: UUID) -> int:
        """Count annotated variants for a sample.

        Args:
            sample_id: Sample UUID

        Returns:
            Number of annotated variants
        """
        ...

    @abstractmethod
    async def get_unique_variant_types(self) -> list[str]:
        """Get all unique variant types from database.

        Returns:
            List of unique variant type strings
        """
        ...
