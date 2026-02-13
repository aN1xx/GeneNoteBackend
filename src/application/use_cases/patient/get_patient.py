"""Get patient use case."""

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.patient import PatientResponse
from src.domain.exceptions import PatientNotFoundError
from src.domain.repositories import IUnitOfWork


@dataclass
class GetPatientUseCase:
    """Use case for getting a patient by ID."""

    uow: IUnitOfWork

    async def execute(self, patient_id: UUID) -> PatientResponse:
        """Execute get patient use case.

        Args:
            patient_id: Patient UUID

        Returns:
            Patient response

        Raises:
            PatientNotFoundError: If patient not found
        """
        async with self.uow:
            patient = await self.uow.patients.get_by_id(patient_id)

            if not patient:
                raise PatientNotFoundError(str(patient_id))

            return PatientResponse(
                id=patient.id,
                name=patient.name,
                sex=patient.sex,
                birth_date=patient.birth_date,
                request_id=patient.request_id,
                analysis_name=patient.analysis_name,
                analysis_date=patient.analysis_date,
                age=patient.age,
                created_at=patient.created_at,
                updated_at=patient.updated_at,
            )


@dataclass
class GetPatientByRequestIdUseCase:
    """Use case for getting a patient by request ID."""

    uow: IUnitOfWork

    async def execute(self, request_id: str) -> PatientResponse:
        """Execute get patient by request ID use case.

        Args:
            request_id: Patient request ID

        Returns:
            Patient response

        Raises:
            PatientNotFoundError: If patient not found
        """
        async with self.uow:
            patient = await self.uow.patients.get_by_request_id(request_id)

            if not patient:
                raise PatientNotFoundError(request_id)

            return PatientResponse(
                id=patient.id,
                name=patient.name,
                sex=patient.sex,
                birth_date=patient.birth_date,
                request_id=patient.request_id,
                analysis_name=patient.analysis_name,
                analysis_date=patient.analysis_date,
                age=patient.age,
                created_at=patient.created_at,
                updated_at=patient.updated_at,
            )
