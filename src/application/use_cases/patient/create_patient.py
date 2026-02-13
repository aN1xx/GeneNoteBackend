"""Create patient use case."""

from dataclasses import dataclass
from uuid import uuid4

from src.application.dto.patient import CreatePatientRequest, PatientResponse
from src.domain.entities import Patient
from src.domain.exceptions import PatientAlreadyExistsError
from src.domain.repositories import IUnitOfWork


@dataclass
class CreatePatientUseCase:
    """Use case for creating a patient."""

    uow: IUnitOfWork

    async def execute(self, request: CreatePatientRequest) -> PatientResponse:
        """Execute create patient use case.

        Args:
            request: Create patient request

        Returns:
            Created patient response

        Raises:
            PatientAlreadyExistsError: If request_id already exists
        """
        async with self.uow:
            if await self.uow.patients.request_id_exists(request.request_id):
                raise PatientAlreadyExistsError(request.request_id)

            patient = Patient(
                id=uuid4(),
                name=request.name,
                sex=request.sex,
                birth_date=request.birth_date,
                request_id=request.request_id,
                analysis_name=request.analysis_name,
                analysis_date=request.analysis_date,
            )

            saved_patient = await self.uow.patients.save(patient)
            await self.uow.commit()

            return PatientResponse(
                id=saved_patient.id,
                name=saved_patient.name,
                sex=saved_patient.sex,
                birth_date=saved_patient.birth_date,
                request_id=saved_patient.request_id,
                analysis_name=saved_patient.analysis_name,
                analysis_date=saved_patient.analysis_date,
                age=saved_patient.age,
                created_at=saved_patient.created_at,
                updated_at=saved_patient.updated_at,
            )
