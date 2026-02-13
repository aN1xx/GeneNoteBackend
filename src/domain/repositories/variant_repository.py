"""Variant repository interface."""

from abc import abstractmethod

from src.domain.entities import GermlineVariant
from src.domain.enums import ACMGClassification
from src.domain.repositories.base import IRepository


class IVariantRepository(IRepository[GermlineVariant]):
    """Repository interface for GermlineVariant entities."""

    @abstractmethod
    async def get_by_coordinates(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> GermlineVariant | None:
        """Get variant by genomic coordinates.

        Args:
            chromosome: Chromosome (1-22, X, Y, MT)
            position: Genomic position (1-based)
            ref: Reference allele
            alt: Alternate allele

        Returns:
            Variant if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_variant_name(self, variant_name: str) -> GermlineVariant | None:
        """Get variant by variant name (chr-pos-ref-alt).

        Args:
            variant_name: Variant name in format chr{chrom}-{pos}-{ref}-{alt}

        Returns:
            Variant if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_gene(
        self,
        gene: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GermlineVariant]:
        """Get variants by gene name.

        Args:
            gene: Gene symbol (e.g., BRCA1, BRCA2)
            limit: Maximum number of variants
            offset: Number of variants to skip

        Returns:
            List of variants in the gene
        """
        ...

    @abstractmethod
    async def get_by_classification(
        self,
        classification: ACMGClassification,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GermlineVariant]:
        """Get variants by ACMG classification.

        Args:
            classification: ACMG classification
            limit: Maximum number of variants
            offset: Number of variants to skip

        Returns:
            List of variants with specified classification
        """
        ...

    @abstractmethod
    async def get_pathogenic(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GermlineVariant]:
        """Get pathogenic and likely pathogenic variants.

        Args:
            limit: Maximum number of variants
            offset: Number of variants to skip

        Returns:
            List of pathogenic variants
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 50,
    ) -> list[GermlineVariant]:
        """Search variants by gene name or variant name.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching variants
        """
        ...

    @abstractmethod
    async def save_many(
        self,
        variants: list[GermlineVariant],
    ) -> list[GermlineVariant]:
        """Save multiple variants in bulk.

        Args:
            variants: List of variants to save

        Returns:
            List of saved variants
        """
        ...

    @abstractmethod
    async def variant_exists(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
    ) -> bool:
        """Check if variant exists by coordinates.

        Args:
            chromosome: Chromosome
            position: Position
            ref: Reference allele
            alt: Alternate allele

        Returns:
            True if variant exists
        """
        ...
