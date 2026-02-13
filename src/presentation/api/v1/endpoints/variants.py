"""Variant API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from src.application.dto.variant import (
    VariantListResponse,
    VariantResponse,
    VariantSearchRequest,
)
from src.application.use_cases.variant import (
    GetPathogenicVariantsUseCase,
    GetVariantByNameUseCase,
    GetVariantUseCase,
    SearchVariantsUseCase,
)
from src.domain.enums import ACMGClassification
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.presentation.dependencies import CurrentUser

router = APIRouter(prefix="/variants", tags=["Variants"])


def get_uow() -> SQLAlchemyUnitOfWork:
    """Get Unit of Work instance."""
    return SQLAlchemyUnitOfWork(async_session_factory)


@router.get(
    "",
    response_model=VariantListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search variants",
    description="Search variants with filters",
)
async def search_variants(
    current_user: CurrentUser,
    gene: str | None = Query(default=None, description="Filter by gene name"),
    classification: ACMGClassification | None = Query(
        default=None, description="Filter by ACMG classification"
    ),
    query: str | None = Query(default=None, description="Search query"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> VariantListResponse:
    """Search variants with optional filters."""
    use_case = SearchVariantsUseCase(uow=get_uow())
    request = VariantSearchRequest(
        gene=gene,
        classification=classification,
        query=query,
        limit=limit,
        offset=offset,
    )
    return await use_case.execute(request)


@router.get(
    "/pathogenic",
    response_model=VariantListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pathogenic variants",
    description="Get all pathogenic and likely pathogenic variants",
)
async def get_pathogenic_variants(
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> VariantListResponse:
    """Get pathogenic variants."""
    use_case = GetPathogenicVariantsUseCase(uow=get_uow())
    return await use_case.execute(limit=limit, offset=offset)


@router.get(
    "/by-name/{variant_name:path}",
    response_model=VariantResponse,
    status_code=status.HTTP_200_OK,
    summary="Get variant by name",
    description="Get variant by its name (chr-pos-ref-alt)",
)
async def get_variant_by_name(
    variant_name: str,
    current_user: CurrentUser,
) -> VariantResponse:
    """Get variant by name (format: chr1-12345-A-G)."""
    use_case = GetVariantByNameUseCase(uow=get_uow())
    return await use_case.execute(variant_name)


@router.get(
    "/{variant_id}",
    response_model=VariantResponse,
    status_code=status.HTTP_200_OK,
    summary="Get variant",
    description="Get variant by ID",
)
async def get_variant(
    variant_id: UUID,
    current_user: CurrentUser,
) -> VariantResponse:
    """Get variant by ID."""
    use_case = GetVariantUseCase(uow=get_uow())
    return await use_case.execute(variant_id)
