"""Patient API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.application.dto.patient import (
    CreatePatientRequest,
    PatientListResponse,
    PatientResponse,
    PatientSearchRequest,
)
from src.application.use_cases.patient import (
    CreatePatientUseCase,
    GetPatientByRequestIdUseCase,
    GetPatientUseCase,
    ListPatientsUseCase,
    SearchPatientsUseCase,
)
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.presentation.dependencies import CurrentUser, LaborantUser

router = APIRouter(prefix="/patients", tags=["Patients"])


def get_uow() -> SQLAlchemyUnitOfWork:
    """Get Unit of Work instance."""
    return SQLAlchemyUnitOfWork(async_session_factory)


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create patient",
    description="Create a new patient record",
)
async def create_patient(
    request: CreatePatientRequest,
    current_user: LaborantUser,
) -> PatientResponse:
    """Create a new patient."""
    use_case = CreatePatientUseCase(uow=get_uow())
    return await use_case.execute(request)


@router.get(
    "",
    response_model=PatientListResponse,
    status_code=status.HTTP_200_OK,
    summary="List patients",
    description="Get paginated list of patients",
)
async def list_patients(
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PatientListResponse:
    """Get list of patients with pagination."""
    use_case = ListPatientsUseCase(uow=get_uow())
    return await use_case.execute(limit=limit, offset=offset)


@router.get(
    "/search",
    response_model=PatientListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search patients",
    description="Search patients by name or date range",
)
async def search_patients(
    current_user: CurrentUser,
    request: Annotated[PatientSearchRequest, Depends()],
) -> PatientListResponse:
    """Search patients with filters."""
    use_case = SearchPatientsUseCase(uow=get_uow())
    return await use_case.execute(request)


@router.get(
    "/by-request-id/{request_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get patient by request ID",
    description="Get patient by their request ID",
)
async def get_patient_by_request_id(
    request_id: str,
    current_user: CurrentUser,
) -> PatientResponse:
    """Get patient by request ID."""
    use_case = GetPatientByRequestIdUseCase(uow=get_uow())
    return await use_case.execute(request_id)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get patient",
    description="Get patient by ID",
)
async def get_patient(
    patient_id: UUID,
    current_user: CurrentUser,
) -> PatientResponse:
    """Get patient by ID."""
    use_case = GetPatientUseCase(uow=get_uow())
    return await use_case.execute(patient_id)
