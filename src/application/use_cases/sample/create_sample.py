"""Create sample use case."""

from dataclasses import dataclass
from uuid import uuid4

from src.application.dto.sample import CreateSampleRequest, SampleResponse
from src.domain.entities import Sample
from src.domain.exceptions import PatientNotFoundError, SampleAlreadyExistsError
from src.domain.repositories import IUnitOfWork


@dataclass
class CreateSampleUseCase:
    """Use case for creating a sample."""

    uow: IUnitOfWork

    async def execute(self, request: CreateSampleRequest) -> SampleResponse:
        """Execute create sample use case.

        Args:
            request: Create sample request

        Returns:
            Created sample response

        Raises:
            PatientNotFoundError: If patient does not exist
            SampleAlreadyExistsError: If sample_code already exists
        """
        async with self.uow:
            # Verify patient exists
            patient = await self.uow.patients.get_by_id(request.patient_id)
            if not patient:
                raise PatientNotFoundError(str(request.patient_id))

            # Check sample code uniqueness
            if await self.uow.samples.sample_code_exists(request.sample_code):
                raise SampleAlreadyExistsError(request.sample_code)

            sample = Sample(
                id=uuid4(),
                patient_id=request.patient_id,
                sample_code=request.sample_code,
                collection_date=request.collection_date,
            )

            saved_sample = await self.uow.samples.save(sample)
            await self.uow.commit()

            has_report = saved_sample.report_path is not None
            is_resequencing_report = (
                bool(saved_sample.requires_resequencing) if has_report else None
            )

            return SampleResponse(
                id=saved_sample.id,
                patient_id=saved_sample.patient_id,
                sample_code=saved_sample.sample_code,
                status=saved_sample.status,
                collection_date=saved_sample.collection_date,
                fastq_r1_path=saved_sample.fastq_r1_path,
                fastq_r2_path=saved_sample.fastq_r2_path,
                tsv_patients_path=saved_sample.tsv_patients_path,
                has_fastq_files=saved_sample.has_fastq_files(),
                can_start_variant_calling=saved_sample.can_start_variant_calling(),
                can_annotate=saved_sample.can_annotate(),
                can_generate_report=saved_sample.can_generate_report(),
                has_report=has_report,
                is_resequencing_report=is_resequencing_report,
                created_at=saved_sample.created_at,
                updated_at=saved_sample.updated_at,
            )
