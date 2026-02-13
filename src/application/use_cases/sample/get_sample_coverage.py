"""Get sample coverage use case."""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.sample import SampleCoverageResponse
from src.domain.exceptions import SampleNotFoundError
from src.domain.repositories import IUnitOfWork


@dataclass
class GetSampleCoverageUseCase:
    """Use case for getting coverage data for a sample."""

    uow: IUnitOfWork

    async def execute(self, sample_id: UUID) -> SampleCoverageResponse:
        """Execute get sample coverage use case.

        Args:
            sample_id: Sample UUID

        Returns:
            Sample coverage response

        Raises:
            SampleNotFoundError: If sample not found
        """
        async with self.uow:
            # First verify that sample exists
            sample = await self.uow.samples.get_by_id(sample_id)
            if not sample:
                raise SampleNotFoundError(str(sample_id))

            # Get coverage data
            coverage = await self.uow.sample_coverages.get_by_sample_id(sample_id)

            if not coverage:
                return SampleCoverageResponse(
                    sample_id=sample_id,
                    has_coverage=False,
                    depth_0x=0.0,
                    depth_5x=0.0,
                    depth_30x=0.0,
                    depth_50x=0.0,
                    depth_100x=0.0,
                    created_at=sample.created_at,
                    updated_at=sample.updated_at,
                )

            return SampleCoverageResponse(
                sample_id=coverage.sample_id,
                has_coverage=True,
                depth_0x=float(coverage.depth_0x),
                depth_5x=float(coverage.depth_5x),
                depth_30x=float(coverage.depth_30x),
                depth_50x=float(coverage.depth_50x),
                depth_100x=float(coverage.depth_100x),
                created_at=coverage.created_at,
                updated_at=coverage.updated_at,
            )
