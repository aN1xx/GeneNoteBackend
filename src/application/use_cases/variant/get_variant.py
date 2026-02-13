"""Get variant use cases."""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.variant import (
    VariantListResponse,
    VariantResponse,
    VariantSearchRequest,
)
from src.domain.exceptions import VariantNotFoundError
from src.domain.repositories import IUnitOfWork


def _to_response(variant) -> VariantResponse:
    """Convert variant entity to response DTO."""
    return VariantResponse(
        id=variant.id,
        chromosome=variant.chromosome,
        position=variant.position,
        ref=variant.ref,
        alt=variant.alt,
        gene=variant.gene,
        variant_name=variant.variant_name,
        variant_type=variant.variant_type,
        transcript=variant.transcript,
        exon_intron=variant.exon_intron,
        hgvs=variant.hgvs,
        hetero_num=variant.hetero_num,
        homo_num=variant.homo_num,
        sample_num=variant.sample_num,
        frequency=variant.frequency,
        pop_freq_gnomad=variant.pop_freq_gnomad,
        acmg_classification=variant.acmg_classification,
        is_pathogenic=variant.is_pathogenic(),
        created_at=variant.created_at,
        updated_at=variant.updated_at,
    )


@dataclass
class GetVariantUseCase:
    """Use case for getting a variant by ID."""

    uow: IUnitOfWork

    async def execute(self, variant_id: UUID) -> VariantResponse:
        """Execute get variant use case.

        Args:
            variant_id: Variant UUID

        Returns:
            Variant response

        Raises:
            VariantNotFoundError: If variant not found
        """
        async with self.uow:
            variant = await self.uow.variants.get_by_id(variant_id)

            if not variant:
                raise VariantNotFoundError(str(variant_id))

            return _to_response(variant)


@dataclass
class GetVariantByNameUseCase:
    """Use case for getting a variant by name."""

    uow: IUnitOfWork

    async def execute(self, variant_name: str) -> VariantResponse:
        """Execute get variant by name use case.

        Args:
            variant_name: Variant name (chr-pos-ref-alt)

        Returns:
            Variant response

        Raises:
            VariantNotFoundError: If variant not found
        """
        async with self.uow:
            variant = await self.uow.variants.get_by_variant_name(variant_name)

            if not variant:
                raise VariantNotFoundError(variant_name)

            return _to_response(variant)


@dataclass
class SearchVariantsUseCase:
    """Use case for searching variants."""

    uow: IUnitOfWork

    async def execute(self, request: VariantSearchRequest) -> VariantListResponse:
        """Execute search variants use case.

        Args:
            request: Search request with filters

        Returns:
            Variant list response
        """
        async with self.uow:
            variants = []

            if request.gene:
                variants = await self.uow.variants.get_by_gene(
                    gene=request.gene,
                    limit=request.limit,
                    offset=request.offset,
                )
            elif request.classification:
                variants = await self.uow.variants.get_by_classification(
                    classification=request.classification,
                    limit=request.limit,
                    offset=request.offset,
                )
            elif request.query:
                variants = await self.uow.variants.search(
                    query=request.query,
                    limit=request.limit,
                )
            else:
                variants = await self.uow.variants.get_all(
                    limit=request.limit,
                    offset=request.offset,
                )

            items = [_to_response(v) for v in variants]
            total = await self.uow.variants.count()

            return VariantListResponse(
                items=items,
                total=total,
                limit=request.limit,
                offset=request.offset,
            )


@dataclass
class GetPathogenicVariantsUseCase:
    """Use case for getting pathogenic variants."""

    uow: IUnitOfWork

    async def execute(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> VariantListResponse:
        """Execute get pathogenic variants use case.

        Args:
            limit: Maximum number of variants
            offset: Number of variants to skip

        Returns:
            Variant list response
        """
        async with self.uow:
            variants = await self.uow.variants.get_pathogenic(
                limit=limit,
                offset=offset,
            )

            items = [_to_response(v) for v in variants]

            return VariantListResponse(
                items=items,
                total=len(items),
                limit=limit,
                offset=offset,
            )
