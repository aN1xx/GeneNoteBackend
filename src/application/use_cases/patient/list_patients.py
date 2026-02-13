"""List patients use case."""

from dataclasses import dataclass

from src.application.dto.patient import (
    PatientListResponse,
    PatientResponse,
    PatientSearchRequest,
)
from src.domain.repositories import IUnitOfWork


@dataclass
class ListPatientsUseCase:
    """Use case for listing patients with pagination."""

    uow: IUnitOfWork

    async def execute(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> PatientListResponse:
        """Execute list patients use case.

        Args:
            limit: Maximum number of patients to return
            offset: Number of patients to skip

        Returns:
            Patient list response with pagination info
        """
        async with self.uow:
            patients = await self.uow.patients.get_all(limit=limit, offset=offset)
            total = await self.uow.patients.count()

            items = [
                PatientResponse(
                    id=p.id,
                    name=p.name,
                    sex=p.sex,
                    birth_date=p.birth_date,
                    request_id=p.request_id,
                    analysis_name=p.analysis_name,
                    analysis_date=p.analysis_date,
                    age=p.age,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
                for p in patients
            ]

            return PatientListResponse(
                items=items,
                total=total,
                limit=limit,
                offset=offset,
            )


@dataclass
class SearchPatientsUseCase:
    """Use case for searching patients."""

    uow: IUnitOfWork

    async def execute(self, request: PatientSearchRequest) -> PatientListResponse:
        """Execute search patients use case.

        Args:
            request: Search request with filters

        Returns:
            Patient list response with matching patients
        """
        async with self.uow:
            patients = []

            if request.name:
                patients = await self.uow.patients.search_by_name(
                    name=request.name,
                    limit=request.limit,
                    offset=request.offset,
                )
            elif request.start_date and request.end_date:
                patients = await self.uow.patients.get_by_date_range(
                    start_date=request.start_date,
                    end_date=request.end_date,
                    limit=request.limit,
                    offset=request.offset,
                )
            else:
                patients = await self.uow.patients.get_all(
                    limit=request.limit,
                    offset=request.offset,
                )

            items = [
                PatientResponse(
                    id=p.id,
                    name=p.name,
                    sex=p.sex,
                    birth_date=p.birth_date,
                    request_id=p.request_id,
                    analysis_name=p.analysis_name,
                    analysis_date=p.analysis_date,
                    age=p.age,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
                for p in patients
            ]

            return PatientListResponse(
                items=items,
                total=len(items),
                limit=request.limit,
                offset=request.offset,
            )
