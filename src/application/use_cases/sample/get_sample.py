"""Get sample use cases."""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.sample import SampleListResponse, SampleResponse
from src.domain.exceptions import SampleNotFoundError
from src.domain.repositories import IUnitOfWork


def _to_response(sample) -> SampleResponse:
    """Convert sample entity to response DTO."""
    has_report = sample.report_path is not None
    is_resequencing_report = bool(sample.requires_resequencing) if has_report else None

    return SampleResponse(
        id=sample.id,
        patient_id=sample.patient_id,
        sample_code=sample.sample_code,
        status=sample.status,
        collection_date=sample.collection_date,
        fastq_r1_path=sample.fastq_r1_path,
        fastq_r2_path=sample.fastq_r2_path,
        tsv_patients_path=sample.tsv_patients_path,
        has_fastq_files=sample.has_fastq_files(),
        can_start_variant_calling=sample.can_start_variant_calling(),
        can_annotate=sample.can_annotate(),
        can_generate_report=sample.can_generate_report(),
        has_report=has_report,
        is_resequencing_report=is_resequencing_report,
        created_at=sample.created_at,
        updated_at=sample.updated_at,
    )


@dataclass
class GetSampleUseCase:
    """Use case for getting a sample by ID."""

    uow: IUnitOfWork

    async def execute(self, sample_id: UUID) -> SampleResponse:
        """Execute get sample use case.

        Args:
            sample_id: Sample UUID

        Returns:
            Sample response

        Raises:
            SampleNotFoundError: If sample not found
        """
        async with self.uow:
            sample = await self.uow.samples.get_by_id(sample_id)

            if not sample:
                raise SampleNotFoundError(str(sample_id))

            return _to_response(sample)


@dataclass
class GetSampleByCodeUseCase:
    """Use case for getting a sample by code."""

    uow: IUnitOfWork

    async def execute(self, sample_code: str) -> SampleResponse:
        """Execute get sample by code use case.

        Args:
            sample_code: Sample code

        Returns:
            Sample response

        Raises:
            SampleNotFoundError: If sample not found
        """
        async with self.uow:
            sample = await self.uow.samples.get_by_sample_code(sample_code)

            if not sample:
                raise SampleNotFoundError(sample_code)

            return _to_response(sample)


@dataclass
class GetSamplesByPatientUseCase:
    """Use case for getting samples by patient ID."""

    uow: IUnitOfWork

    async def execute(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> SampleListResponse:
        """Execute get samples by patient use case.

        Args:
            patient_id: Patient UUID
            limit: Maximum number of samples
            offset: Number of samples to skip

        Returns:
            Sample list response
        """
        async with self.uow:
            samples = await self.uow.samples.get_by_patient_id(
                patient_id=patient_id,
                limit=limit,
                offset=offset,
            )

            items = [_to_response(s) for s in samples]

            return SampleListResponse(
                items=items,
                total=len(items),
                limit=limit,
                offset=offset,
            )


@dataclass
class GetAllSamplesUseCase:
    """Use case for getting all samples."""

    uow: IUnitOfWork

    async def execute(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> SampleListResponse:
        """Execute get all samples use case.

        Args:
            limit: Maximum number of samples
            offset: Number of samples to skip

        Returns:
            Sample list response
        """
        async with self.uow:
            samples = await self.uow.samples.get_all(
                limit=limit,
                offset=offset,
            )

            total_count = await self.uow.samples.count()

            items = [_to_response(s) for s in samples]

            return SampleListResponse(
                items=items,
                total=total_count,
                limit=limit,
                offset=offset,
            )


@dataclass
class GetAwaitingAnnotationSamplesUseCase:
    """Use case for getting samples awaiting annotation."""

    uow: IUnitOfWork

    async def execute(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> SampleListResponse:
        """Execute get awaiting annotation samples use case.

        Args:
            limit: Maximum number of samples
            offset: Number of samples to skip

        Returns:
            Sample list response
        """
        async with self.uow:
            samples = await self.uow.samples.get_awaiting_annotation(
                limit=limit,
                offset=offset,
            )

            items = [_to_response(s) for s in samples]

            return SampleListResponse(
                items=items,
                total=len(items),
                limit=limit,
                offset=offset,
            )
