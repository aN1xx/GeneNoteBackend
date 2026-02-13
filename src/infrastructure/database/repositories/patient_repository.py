"""Patient repository implementation."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities import Patient
from src.domain.repositories import IPatientRepository
from src.infrastructure.database.models import PatientModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemyPatientRepository(SQLAlchemyRepository[PatientModel, Patient], IPatientRepository):
    """SQLAlchemy implementation of Patient repository."""

    model_class = PatientModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_request_id(self, request_id: str) -> Patient | None:
        """Get patient by request ID."""
        stmt = select(PatientModel).where(PatientModel.request_id == request_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def search_by_name(
        self,
        name: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Patient]:
        """Search patients by name (partial match)."""
        stmt = (
            select(PatientModel)
            .where(PatientModel.name.ilike(f"%{name}%"))
            .order_by(PatientModel.name)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Patient]:
        """Get patients created within date range."""
        stmt = (
            select(PatientModel)
            .where(
                PatientModel.created_at >= start_date,
                PatientModel.created_at <= end_date,
            )
            .order_by(PatientModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_with_variants(self, patient_id: UUID) -> Patient | None:
        """Get patient with their variant IDs loaded."""
        stmt = (
            select(PatientModel)
            .options(selectinload(PatientModel.patient_variants))
            .where(PatientModel.id == patient_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            entity = self._to_entity(model)
            entity.variant_ids = [pv.variant_id for pv in model.patient_variants]  # type: ignore[misc]
            return entity
        return None

    async def request_id_exists(
        self,
        request_id: str,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if request ID already exists."""
        stmt = select(func.count()).where(PatientModel.request_id == request_id)
        if exclude_id:
            stmt = stmt.where(PatientModel.id != exclude_id)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count is not None and count > 0

    def _to_entity(self, model: PatientModel) -> Patient:
        """Convert ORM model to domain entity."""
        return Patient(
            id=model.id,
            name=model.name,
            sex=model.sex,
            birth_date=model.birth_date,
            request_id=model.request_id,
            analysis_name=model.analysis_name,
            analysis_date=model.analysis_date,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Patient) -> PatientModel:
        """Convert domain entity to ORM model."""
        return PatientModel(
            id=entity.id,
            name=entity.name,
            sex=entity.sex,
            birth_date=entity.birth_date,
            request_id=entity.request_id,
            analysis_name=entity.analysis_name,
            analysis_date=entity.analysis_date,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
