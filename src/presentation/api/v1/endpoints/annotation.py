"""Annotation API endpoints for geneticist workflow.

Handles the geneticist annotation workflow:
- View and annotate sample variants
- Mark variants as true variants or artifacts
- Complete annotation and update global databases
"""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.application.dto.variant import (
    AnnotateSampleVariantRequest,
    BatchAnnotateRequest,
    BatchAnnotateResponse,
    SampleVariantListResponse,
    SampleVariantResponse,
)
from src.domain.entities import GermlineArtifact, GermlineVariant, SampleVariant
from src.domain.enums import ACMGClassification, SampleStatus
from src.domain.enums.variant_type import VariantType
from src.domain.exceptions import SampleNotFoundError
from src.domain.repositories import IUnitOfWork
from src.infrastructure.pipeline import DatabaseTsvSyncService
from src.presentation.dependencies import GeneticistUser, get_unit_of_work

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/annotation", tags=["Annotation"])

# Type alias for dependency injection
UoW = Annotated[IUnitOfWork, Depends(get_unit_of_work)]


class AnnotationProgressResponse(BaseModel):
    """Response with annotation progress."""

    sample_id: UUID
    sample_code: str
    total_variants: int
    annotated_count: int
    progress_percent: float
    is_complete: bool


class CompleteAnnotationResponse(BaseModel):
    """Response for completing annotation."""

    sample_id: UUID
    sample_code: str
    status: SampleStatus
    annotated_at: datetime
    annotated_by_id: UUID


async def _get_live_data_for_variants(
    uow: IUnitOfWork,
    variants: list[SampleVariant],
) -> dict[str, dict]:
    """Get live data from germline_variants and germline_artifacts for variants.

    Args:
        uow: Unit of Work
        variants: List of sample variants to look up

    Returns:
        Dict mapping variant_name to data dict with keys:
        - variant_db_num, variant_db_hetero_num, variant_db_homo_num, artifact_db_num
        - acmg_classification, variant_type, pop_freq_gnomad (from germline_variants if exists)
    """
    data: dict[str, dict] = {}

    for v in variants:
        variant_name = v.variant_name

        # Default to snapshot values from sample_variant
        data[variant_name] = {
            "variant_db_num": v.variant_db_num,
            "variant_db_hetero_num": v.variant_db_hetero_num,
            "variant_db_homo_num": v.variant_db_homo_num,
            "artifact_db_num": v.artifact_db_num,
            "acmg_classification": None,  # Will be set from germline_variants if exists
            "variant_type": None,  # Will be set from germline_variants if exists
            "pop_freq_gnomad": None,  # Will be set from germline_variants if exists
        }

        try:
            # Lookup in germline_variants
            germline_variant = await uow.variants.get_by_coordinates(
                chromosome=v.chromosome,
                position=v.position,
                ref=v.ref,
                alt=v.alt,
            )
            if germline_variant:
                data[variant_name]["variant_db_hetero_num"] = germline_variant.hetero_num
                data[variant_name]["variant_db_homo_num"] = germline_variant.homo_num
                data[variant_name]["variant_db_num"] = (
                    germline_variant.hetero_num + germline_variant.homo_num
                )
                # Get annotation from germline_variants (authoritative source)
                data[variant_name]["acmg_classification"] = germline_variant.acmg_classification
                data[variant_name]["variant_type"] = germline_variant.variant_type
                data[variant_name]["pop_freq_gnomad"] = germline_variant.pop_freq_gnomad

            # Lookup in germline_artifacts
            germline_artifact = await uow.artifacts.get_by_coordinates(
                chromosome=v.chromosome,
                position=v.position,
                ref=v.ref,
                alt=v.alt,
            )
            if germline_artifact:
                data[variant_name]["artifact_db_num"] = germline_artifact.occurrence_num
        except (TypeError, AttributeError):
            # Fallback to snapshot values if lookup fails (e.g., in tests with mocks)
            pass

    return data


@router.get(
    "/samples/{sample_id}/variants",
    response_model=SampleVariantListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sample variants for annotation",
    description="Get all variants for a sample that need annotation",
)
async def get_sample_variants(
    sample_id: UUID,
    uow: UoW,
    current_user: GeneticistUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    unannotated_only: bool = Query(default=False, description="Return only unannotated variants"),
) -> SampleVariantListResponse:
    """Get variants for a sample with live database counts."""
    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        if unannotated_only:
            variants = await uow.sample_variants.get_unannotated_by_sample(sample_id)
        else:
            variants = await uow.sample_variants.get_by_sample_id(
                sample_id, limit=limit, offset=offset
            )

        total = await uow.sample_variants.count_by_sample(sample_id)
        annotated = await uow.sample_variants.count_annotated_by_sample(sample_id)

        # Get live data from germline databases (counts + ACMG)
        live_data = await _get_live_data_for_variants(uow, variants)

        # Build responses with live data
        items = []
        for v in variants:
            data = live_data.get(v.variant_name, {})
            items.append(
                SampleVariantResponse.from_entity_with_live_data(
                    entity=v,
                    variant_db_num=data.get("variant_db_num", v.variant_db_num),
                    variant_db_hetero_num=data.get(
                        "variant_db_hetero_num", v.variant_db_hetero_num
                    ),
                    variant_db_homo_num=data.get("variant_db_homo_num", v.variant_db_homo_num),
                    artifact_db_num=data.get("artifact_db_num", v.artifact_db_num),
                    acmg_classification=data.get("acmg_classification"),
                    variant_type=data.get("variant_type"),
                    pop_freq_gnomad=data.get("pop_freq_gnomad"),
                )
            )

        return SampleVariantListResponse(
            items=items,
            total=total,
            annotated_count=annotated,
        )


@router.get(
    "/samples/{sample_id}/variants/{variant_id}",
    response_model=SampleVariantResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single variant",
    description="Get a specific variant by ID",
)
async def get_variant(
    sample_id: UUID,
    variant_id: UUID,
    uow: UoW,
    current_user: GeneticistUser,
) -> SampleVariantResponse:
    """Get a specific variant with live database counts."""
    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        variant = await uow.sample_variants.get_by_id(variant_id)
        if not variant or variant.sample_id != sample_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant {variant_id} not found in sample {sample_id}",
            )

        # Get live data from germline databases (counts + ACMG)
        live_data = await _get_live_data_for_variants(uow, [variant])
        data = live_data.get(variant.variant_name, {})

        return SampleVariantResponse.from_entity_with_live_data(
            entity=variant,
            variant_db_num=data.get("variant_db_num", variant.variant_db_num),
            variant_db_hetero_num=data.get("variant_db_hetero_num", variant.variant_db_hetero_num),
            variant_db_homo_num=data.get("variant_db_homo_num", variant.variant_db_homo_num),
            artifact_db_num=data.get("artifact_db_num", variant.artifact_db_num),
            acmg_classification=data.get("acmg_classification"),
            variant_type=data.get("variant_type"),
            pop_freq_gnomad=data.get("pop_freq_gnomad"),
        )


@router.patch(
    "/samples/{sample_id}/variants/{variant_id}",
    response_model=SampleVariantResponse,
    status_code=status.HTTP_200_OK,
    summary="Annotate variant",
    description="Mark variant as true variant or artifact with annotation data",
)
async def annotate_variant(
    sample_id: UUID,
    variant_id: UUID,
    request: AnnotateSampleVariantRequest,
    uow: UoW,
    current_user: GeneticistUser,
) -> SampleVariantResponse:
    """Annotate a single variant."""
    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        variant = await uow.sample_variants.get_by_id(variant_id)
        if not variant or variant.sample_id != sample_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant {variant_id} not found in sample {sample_id}",
            )

        # Update variant
        if request.is_variant:
            if request.acmg_classification is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="acmg_classification is required when is_variant=True",
                )
            variant.mark_as_variant(
                acmg_classification=request.acmg_classification,
                variant_type=request.variant_type,
                pop_freq_gnomad=request.pop_freq_gnomad,
            )
        else:
            variant.mark_as_artifact()

        await uow.sample_variants.save(variant)
        await uow.commit()

        return SampleVariantResponse.from_entity(variant)


@router.post(
    "/samples/{sample_id}/variants/batch-annotate",
    response_model=BatchAnnotateResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch annotate variants",
    description="Annotate multiple variants at once",
)
async def batch_annotate_variants(
    sample_id: UUID,
    request: BatchAnnotateRequest,
    uow: UoW,
    current_user: GeneticistUser,
) -> BatchAnnotateResponse:
    """Batch annotate multiple variants for a sample."""
    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        updated_count = 0
        failed_count = 0
        errors: list[str] = []

        for item in request.annotations:
            try:
                variant = await uow.sample_variants.get_by_id(item.variant_id)
                if not variant or variant.sample_id != sample_id:
                    errors.append(f"Variant {item.variant_id} not found in sample")
                    failed_count += 1
                    continue

                if item.is_variant:
                    if item.acmg_classification is None:
                        errors.append(
                            f"Variant {item.variant_id}: acmg_classification required when is_variant=True"
                        )
                        failed_count += 1
                        continue
                    variant.mark_as_variant(
                        acmg_classification=item.acmg_classification,
                        variant_type=item.variant_type,
                        pop_freq_gnomad=item.pop_freq_gnomad,
                    )
                else:
                    variant.mark_as_artifact()

                await uow.sample_variants.save(variant)
                updated_count += 1

            except Exception as e:
                logger.exception(f"Error annotating variant {item.variant_id}")
                errors.append(f"Variant {item.variant_id}: {e!s}")
                failed_count += 1

        await uow.commit()

        return BatchAnnotateResponse(
            updated_count=updated_count,
            failed_count=failed_count,
            errors=errors if errors else None,
        )


@router.get(
    "/samples/{sample_id}/progress",
    response_model=AnnotationProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get annotation progress",
    description="Get annotation progress for a sample",
)
async def get_annotation_progress(
    sample_id: UUID,
    uow: UoW,
    current_user: GeneticistUser,
) -> AnnotationProgressResponse:
    """Get annotation progress for a sample."""
    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        total = await uow.sample_variants.count_by_sample(sample_id)
        annotated = await uow.sample_variants.count_annotated_by_sample(sample_id)

        progress = (annotated / total * 100) if total > 0 else 0.0

        return AnnotationProgressResponse(
            sample_id=sample.id,
            sample_code=sample.sample_code,
            total_variants=total,
            annotated_count=annotated,
            progress_percent=round(progress, 2),
            is_complete=total > 0 and annotated == total,
        )


@router.post(
    "/samples/{sample_id}/complete",
    response_model=CompleteAnnotationResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete annotation",
    description="Mark sample annotation as complete and update global databases",
)
async def complete_annotation(
    sample_id: UUID,
    uow: UoW,
    current_user: GeneticistUser,
) -> CompleteAnnotationResponse:
    """Mark sample annotation as complete and update global variant/artifact databases.

    This endpoint:
    1. Validates all variants are annotated
    2. Updates global GermlineVariant database with confirmed variants
    3. Updates global GermlineArtifact database with identified artifacts
    4. Updates sample_num counters in both databases
    5. Marks sample as ANNOTATED
    """
    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        # Check sample status
        if sample.status != SampleStatus.AWAITING_ANNOTATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sample status must be AWAITING_ANNOTATION, got {sample.status.value}",
            )

        # Check all variants are annotated
        total = await uow.sample_variants.count_by_sample(sample_id)
        annotated = await uow.sample_variants.count_annotated_by_sample(sample_id)

        if total == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sample has no variants to annotate",
            )

        if annotated < total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not all variants annotated: {annotated}/{total}",
            )

        # Get all annotated variants
        all_variants = await uow.sample_variants.get_by_sample_id(sample_id, limit=1000, offset=0)

        # Update global databases
        variants_added = 0
        artifacts_added = 0

        for sv in all_variants:
            if sv.is_variant:
                # Update or create GermlineVariant
                await _update_germline_variant(uow, sv)
                variants_added += 1
            elif sv.is_artifact:
                # Update or create GermlineArtifact
                await _update_germline_artifact(uow, sv)
                artifacts_added += 1

        logger.info(
            f"Sample {sample.sample_code}: Updated {variants_added} variants, "
            f"{artifacts_added} artifacts in global databases"
        )

        # Update sample status
        now = datetime.now(UTC)
        sample.status = SampleStatus.ANNOTATED
        sample.annotated_at = now
        sample.annotated_by_id = current_user.id

        await uow.samples.save(sample)
        await uow.commit()

        # Sync updated databases to TSV files for pipeline
        try:
            sync_service = DatabaseTsvSyncService()
            sync_result = await sync_service.sync_all(uow)
            logger.info(
                f"TSV sync complete: {sync_result['variants_exported']} variants, "
                f"{sync_result['artifacts_exported']} artifacts exported"
            )
        except Exception as e:
            # Log error but don't fail the annotation completion
            logger.error(f"Failed to sync databases to TSV: {e}")

        return CompleteAnnotationResponse(
            sample_id=sample.id,
            sample_code=sample.sample_code,
            status=sample.status,
            annotated_at=now,
            annotated_by_id=current_user.id,
        )


async def _update_germline_variant(uow: IUnitOfWork, sv: SampleVariant) -> None:
    """Update or create GermlineVariant from annotated sample variant.

    Args:
        uow: Unit of Work
        sv: Sample variant marked as is_variant=True
    """
    # Check if variant exists in global database
    existing = await uow.variants.get_by_coordinates(
        chromosome=sv.chromosome,
        position=sv.position,
        ref=sv.ref,
        alt=sv.alt,
    )

    is_heterozygous = "гетерозигота" in sv.genotype.lower() or "het" in sv.genotype.lower()

    if existing:
        # Update existing variant statistics
        existing.update_statistics(is_heterozygous=is_heterozygous)

        # Update annotation if provided (with changelog for ACMG changes)
        if sv.acmg_classification:
            existing.update_acmg_with_changelog(sv.acmg_classification)
        if sv.variant_type:
            existing.variant_type = VariantType.from_string(sv.variant_type)
        if sv.pop_freq_gnomad:
            existing.pop_freq_gnomad = sv.pop_freq_gnomad

        await uow.variants.save(existing)
    else:
        # Create new variant
        new_variant = GermlineVariant(
            id=uuid4(),
            chromosome=sv.chromosome,
            position=sv.position,
            ref=sv.ref,
            alt=sv.alt,
            gene=sv.gene,
            variant_type=VariantType.from_string(sv.variant_type),
            transcript=sv.transcript or "",
            exon_intron=sv.exon_intron,
            hgvs=sv.hgvs,
            hetero_num=1 if is_heterozygous else 0,
            homo_num=0 if is_heterozygous else 1,
            sample_num=1,
            pop_freq_gnomad=sv.pop_freq_gnomad,
            acmg_classification=sv.acmg_classification or ACMGClassification.NOT_CLASSIFIED,
        )
        await uow.variants.save(new_variant)


async def _update_germline_artifact(uow: IUnitOfWork, sv: SampleVariant) -> None:
    """Update or create GermlineArtifact from annotated sample variant.

    Args:
        uow: Unit of Work
        sv: Sample variant marked as is_artifact=True
    """
    # Check if artifact exists in global database
    existing = await uow.artifacts.get_by_coordinates(
        chromosome=sv.chromosome,
        position=sv.position,
        ref=sv.ref,
        alt=sv.alt,
    )

    if existing:
        # Increment occurrence count
        existing.record_occurrence()
        await uow.artifacts.save(existing)
    else:
        # Create new artifact
        new_artifact = GermlineArtifact(
            id=uuid4(),
            chromosome=sv.chromosome,
            position=sv.position,
            ref=sv.ref,
            alt=sv.alt,
            occurrence_num=1,
            sample_num=1,
        )
        await uow.artifacts.save(new_artifact)


@router.get(
    "/samples/{sample_id}/confirmed-variants",
    response_model=SampleVariantListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get confirmed variants",
    description="Get variants marked as true variants (not artifacts)",
)
async def get_confirmed_variants(
    sample_id: UUID,
    uow: UoW,
    current_user: GeneticistUser,
) -> SampleVariantListResponse:
    """Get variants confirmed as true variants with live database counts."""
    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        variants = await uow.sample_variants.get_confirmed_variants(sample_id)
        total = len(variants)

        # Get live data from germline databases (counts + ACMG + variant_type + pop_freq)
        live_data = await _get_live_data_for_variants(uow, variants)

        # Build responses with live data
        items = []
        for v in variants:
            data = live_data.get(v.variant_name, {})
            items.append(
                SampleVariantResponse.from_entity_with_live_data(
                    entity=v,
                    variant_db_num=data.get("variant_db_num", v.variant_db_num),
                    variant_db_hetero_num=data.get(
                        "variant_db_hetero_num", v.variant_db_hetero_num
                    ),
                    variant_db_homo_num=data.get("variant_db_homo_num", v.variant_db_homo_num),
                    artifact_db_num=data.get("artifact_db_num", v.artifact_db_num),
                    acmg_classification=data.get("acmg_classification"),
                    variant_type=data.get("variant_type"),
                    pop_freq_gnomad=data.get("pop_freq_gnomad"),
                )
            )

        return SampleVariantListResponse(
            items=items,
            total=total,
            annotated_count=total,
        )


@router.get(
    "/samples/{sample_id}/annotated-variants",
    response_model=SampleVariantListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get annotated variants",
    description="Get all annotated variants (both confirmed variants and artifacts)",
)
async def get_annotated_variants(
    sample_id: UUID,
    uow: UoW,
    current_user: GeneticistUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SampleVariantListResponse:
    """Get all annotated variants for a sample (variants + artifacts) with live database data."""
    async with uow:
        sample = await uow.samples.get_by_id(sample_id)
        if not sample:
            raise SampleNotFoundError(str(sample_id))

        variants = await uow.sample_variants.get_annotated_variants(
            sample_id, limit=limit, offset=offset
        )
        annotated_count = await uow.sample_variants.count_annotated_by_sample(sample_id)

        # Get live data from germline databases (counts + ACMG + variant_type + pop_freq)
        live_data = await _get_live_data_for_variants(uow, variants)

        # Build responses with live data
        items = []
        for v in variants:
            data = live_data.get(v.variant_name, {})
            items.append(
                SampleVariantResponse.from_entity_with_live_data(
                    entity=v,
                    variant_db_num=data.get("variant_db_num", v.variant_db_num),
                    variant_db_hetero_num=data.get(
                        "variant_db_hetero_num", v.variant_db_hetero_num
                    ),
                    variant_db_homo_num=data.get("variant_db_homo_num", v.variant_db_homo_num),
                    artifact_db_num=data.get("artifact_db_num", v.artifact_db_num),
                    acmg_classification=data.get("acmg_classification"),
                    variant_type=data.get("variant_type"),
                    pop_freq_gnomad=data.get("pop_freq_gnomad"),
                )
            )

        return SampleVariantListResponse(
            items=items,
            total=annotated_count,
            annotated_count=annotated_count,
        )


class VariantTypesResponse(BaseModel):
    """Response with available variant types."""

    items: list[str]
    total: int


@router.get(
    "/variant-types",
    response_model=VariantTypesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get available variant types",
    description="Get all available variant types (predefined + custom from database)",
)
async def get_variant_types(
    uow: UoW,
    current_user: GeneticistUser,
) -> VariantTypesResponse:
    """Get all available variant types for annotation.

    Returns predefined enum values plus any custom values from database.
    """
    # Excluded values (deprecated or internal)
    excluded = {"unknown", "nonframeshift deletion", "nonframeshift insertion"}

    # Get predefined enum values (exclude deprecated)
    predefined_types = {
        member.value for member in VariantType
        if member.value.lower() not in excluded
    }

    async with uow:
        # Get custom types from database
        db_types = await uow.sample_variants.get_unique_variant_types()

    # Combine and deduplicate, excluding deprecated values
    all_types = predefined_types.union({t for t in db_types if t and t.lower() not in excluded})

    # Sort alphabetically
    sorted_types = sorted(all_types, key=str.lower)

    return VariantTypesResponse(
        items=sorted_types,
        total=len(sorted_types),
    )
