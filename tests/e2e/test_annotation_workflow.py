"""E2E tests for annotation workflow.

Tests the full geneticist workflow:
1. Get sample variants for annotation
2. Annotate individual variants
3. Check annotation progress
4. Complete annotation
5. Generate report
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.domain.entities import Sample, SampleVariant
from src.domain.enums import ACMGClassification, SampleStatus


class TestAnnotationWorkflow:
    """E2E tests for complete annotation workflow."""

    @pytest.mark.asyncio
    async def test_get_sample_variants(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
    ) -> None:
        """Test getting sample variants for annotation."""
        response = await geneticist_client.get(
            f"/api/v1/annotation/samples/{test_sample.id}/variants"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(test_variants)
        assert len(data["items"]) == len(test_variants)
        assert data["annotated_count"] == 0

    @pytest.mark.asyncio
    async def test_get_unannotated_variants_only(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
    ) -> None:
        """Test getting only unannotated variants."""
        response = await geneticist_client.get(
            f"/api/v1/annotation/samples/{test_sample.id}/variants",
            params={"unannotated_only": True},
        )

        assert response.status_code == 200
        data = response.json()
        # Should return unannotated variants
        assert len(data["items"]) == len(test_variants)

    @pytest.mark.asyncio
    async def test_annotate_variant_as_pathogenic(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test annotating variant as pathogenic variant."""
        variant = test_variants[0]

        response = await geneticist_client.patch(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/{variant.id}",
            json={
                "is_variant": True,
                "acmg_classification": ACMGClassification.PATHOGENIC.value,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(variant.id)

    @pytest.mark.asyncio
    async def test_annotate_variant_as_artifact(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test annotating variant as artifact."""
        variant = test_variants[1]

        response = await geneticist_client.patch(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/{variant.id}",
            json={
                "is_variant": False,
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_annotate_variant_requires_acmg_when_is_variant(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
    ) -> None:
        """Test that ACMG classification is required when marking as variant."""
        variant = test_variants[0]

        response = await geneticist_client.patch(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/{variant.id}",
            json={
                "is_variant": True,
                # Missing acmg_classification
            },
        )

        assert response.status_code == 400
        assert "acmg" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_annotation_progress(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
    ) -> None:
        """Test getting annotation progress."""
        response = await geneticist_client.get(
            f"/api/v1/annotation/samples/{test_sample.id}/progress"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sample_id"] == str(test_sample.id)
        assert data["total_variants"] == len(test_variants)
        assert data["annotated_count"] == 0
        assert data["progress_percent"] == 0.0
        assert data["is_complete"] is False

    @pytest.mark.asyncio
    async def test_complete_annotation_fails_if_not_all_annotated(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        mock_uow,
    ) -> None:
        """Test that completing annotation fails if not all variants annotated."""
        # Mock: 2 total, 1 annotated
        mock_uow.sample_variants.count_by_sample = AsyncMock(return_value=2)
        mock_uow.sample_variants.count_annotated_by_sample = AsyncMock(return_value=1)

        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/complete"
        )

        assert response.status_code == 400
        assert "Not all variants annotated" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_complete_annotation_success(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        geneticist_user,
        mock_uow,
    ) -> None:
        """Test successfully completing annotation when all variants annotated."""
        # Mock: all variants annotated
        mock_uow.sample_variants.count_by_sample = AsyncMock(return_value=2)
        mock_uow.sample_variants.count_annotated_by_sample = AsyncMock(return_value=2)

        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/complete"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sample_id"] == str(test_sample.id)
        assert data["status"] == SampleStatus.ANNOTATED.value
        assert data["annotated_by_id"] == str(geneticist_user.id)

    @pytest.mark.asyncio
    async def test_get_confirmed_variants(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test getting confirmed (non-artifact) variants."""
        # Mock: first variant confirmed
        confirmed_variant = test_variants[0]
        confirmed_variant.is_variant = True
        confirmed_variant.acmg_classification = ACMGClassification.PATHOGENIC
        mock_uow.sample_variants.get_confirmed_variants = AsyncMock(
            return_value=[confirmed_variant]
        )

        response = await geneticist_client.get(
            f"/api/v1/annotation/samples/{test_sample.id}/confirmed-variants"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1


class TestBatchAnnotation:
    """Tests for batch annotation endpoint."""

    @pytest.mark.asyncio
    async def test_batch_annotate_variants_success(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test batch annotating multiple variants successfully."""

        # Setup mock to return correct variant for each ID
        async def get_variant_by_id(variant_id):
            for v in test_variants:
                if v.id == variant_id:
                    return v
            return None

        mock_uow.sample_variants.get_by_id = AsyncMock(side_effect=get_variant_by_id)

        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/batch-annotate",
            json={
                "annotations": [
                    {
                        "variant_id": str(test_variants[0].id),
                        "is_variant": True,
                        "acmg_classification": ACMGClassification.PATHOGENIC.value,
                    },
                    {
                        "variant_id": str(test_variants[1].id),
                        "is_variant": False,
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 2
        assert data["failed_count"] == 0
        assert data["errors"] is None

    @pytest.mark.asyncio
    async def test_batch_annotate_with_all_fields(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test batch annotation with all optional fields."""
        mock_uow.sample_variants.get_by_id = AsyncMock(return_value=test_variants[0])

        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/batch-annotate",
            json={
                "annotations": [
                    {
                        "variant_id": str(test_variants[0].id),
                        "is_variant": True,
                        "acmg_classification": ACMGClassification.LIKELY_PATHOGENIC.value,
                        "variant_type": "missense",
                        "pop_freq_gnomad": "0.0001",
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 1
        assert data["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_batch_annotate_partial_failure(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test batch annotation with some variants failing."""

        # First variant found, second not found
        async def get_variant_by_id(variant_id):
            if variant_id == test_variants[0].id:
                return test_variants[0]
            return None

        mock_uow.sample_variants.get_by_id = AsyncMock(side_effect=get_variant_by_id)

        non_existent_id = "00000000-0000-0000-0000-000000000000"
        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/batch-annotate",
            json={
                "annotations": [
                    {
                        "variant_id": str(test_variants[0].id),
                        "is_variant": True,
                        "acmg_classification": ACMGClassification.VUS.value,
                    },
                    {
                        "variant_id": non_existent_id,
                        "is_variant": False,
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 1
        assert data["failed_count"] == 1
        assert data["errors"] is not None
        assert len(data["errors"]) == 1
        assert non_existent_id in data["errors"][0]

    @pytest.mark.asyncio
    async def test_batch_annotate_missing_acmg_for_variant(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test that missing ACMG classification causes failure for is_variant=True."""
        mock_uow.sample_variants.get_by_id = AsyncMock(return_value=test_variants[0])

        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/batch-annotate",
            json={
                "annotations": [
                    {
                        "variant_id": str(test_variants[0].id),
                        "is_variant": True,
                        # Missing acmg_classification
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 0
        assert data["failed_count"] == 1
        assert data["errors"] is not None
        assert "acmg_classification" in data["errors"][0].lower()

    @pytest.mark.asyncio
    async def test_batch_annotate_empty_list_fails(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
    ) -> None:
        """Test that empty annotations list returns validation error."""
        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/batch-annotate",
            json={"annotations": []},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_batch_annotate_sample_not_found(
        self,
        geneticist_client: AsyncClient,
        mock_uow,
    ) -> None:
        """Test batch annotation returns 404 for non-existent sample."""
        mock_uow.samples.get_by_id = AsyncMock(return_value=None)

        non_existent_sample = "00000000-0000-0000-0000-000000000000"
        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{non_existent_sample}/variants/batch-annotate",
            json={
                "annotations": [
                    {
                        "variant_id": "00000000-0000-0000-0000-000000000001",
                        "is_variant": False,
                    },
                ]
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_batch_annotate_variant_from_wrong_sample(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test that variant from different sample is rejected."""
        # Create variant with different sample_id
        from uuid import uuid4

        wrong_sample_variant = SampleVariant(
            id=uuid4(),
            sample_id=uuid4(),  # Different sample
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="TEST",
            variant_type="SNV",
            transcript="NM_001",
            depth=100,
            genotype="0/1",
            variant_caller="GATK",
            variant_db_num=0,
            variant_db_hetero_num=0,
            variant_db_homo_num=0,
            artifact_db_num=0,
        )
        mock_uow.sample_variants.get_by_id = AsyncMock(return_value=wrong_sample_variant)

        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/batch-annotate",
            json={
                "annotations": [
                    {
                        "variant_id": str(wrong_sample_variant.id),
                        "is_variant": False,
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 0
        assert data["failed_count"] == 1
        assert "not found in sample" in data["errors"][0]

    @pytest.mark.asyncio
    async def test_batch_annotate_all_artifacts(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_variants: list[SampleVariant],
        mock_uow,
    ) -> None:
        """Test batch annotating all variants as artifacts."""

        async def get_variant_by_id(variant_id):
            for v in test_variants:
                if v.id == variant_id:
                    return v
            return None

        mock_uow.sample_variants.get_by_id = AsyncMock(side_effect=get_variant_by_id)

        response = await geneticist_client.post(
            f"/api/v1/annotation/samples/{test_sample.id}/variants/batch-annotate",
            json={
                "annotations": [
                    {"variant_id": str(v.id), "is_variant": False} for v in test_variants
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == len(test_variants)
        assert data["failed_count"] == 0


class TestReportGeneration:
    """E2E tests for report generation."""

    @pytest.mark.asyncio
    async def test_generate_report_requires_annotated_status(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        mock_uow,
    ) -> None:
        """Test that report generation requires ANNOTATED status."""
        # Sample is in AWAITING_ANNOTATION status
        response = await geneticist_client.post(
            f"/api/v1/reports/samples/{test_sample.id}/generate"
        )

        assert response.status_code == 422  # ValidationError returns 422
        assert "annotated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_preview_report(
        self,
        geneticist_client: AsyncClient,
        test_sample: Sample,
        test_patient,
        test_variants: list[SampleVariant],
        test_coverage,
        mock_uow,
    ) -> None:
        """Test previewing report for annotated sample."""
        # Update sample status to allow preview
        test_sample.status = SampleStatus.ANNOTATED

        with patch(
            "src.application.use_cases.report.preview_report.ReportGenerator"
        ) as mock_generator:
            mock_instance = mock_generator.return_value
            mock_instance.generate_report_bytes.return_value = b"%PDF-1.4..."

            response = await geneticist_client.get(
                f"/api/v1/reports/samples/{test_sample.id}/preview"
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "inline" in response.headers["content-disposition"]
