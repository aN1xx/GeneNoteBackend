"""Sample repository implementation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Sample
from src.domain.enums import SampleStatus
from src.domain.repositories import ISampleRepository
from src.infrastructure.database.models import SampleModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemySampleRepository(SQLAlchemyRepository[SampleModel, Sample], ISampleRepository):
    """SQLAlchemy implementation of Sample repository."""

    model_class = SampleModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_patient_id(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Sample]:
        """Get samples by patient ID."""
        stmt = (
            select(SampleModel)
            .where(SampleModel.patient_id == patient_id)
            .order_by(SampleModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_sample_code(self, sample_code: str) -> Sample | None:
        """Get sample by sample code."""
        stmt = select(SampleModel).where(SampleModel.sample_code == sample_code)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_status(
        self,
        status: SampleStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Sample]:
        """Get samples by status."""
        stmt = (
            select(SampleModel)
            .where(SampleModel.status == status)
            .order_by(SampleModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_awaiting_annotation(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Sample]:
        """Get samples awaiting annotation."""
        return await self.get_by_status(SampleStatus.AWAITING_ANNOTATION, limit, offset)

    async def sample_code_exists(
        self,
        sample_code: str,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if sample code already exists."""
        stmt = select(func.count()).where(SampleModel.sample_code == sample_code)
        if exclude_id:
            stmt = stmt.where(SampleModel.id != exclude_id)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count is not None and count > 0

    def _to_entity(self, model: SampleModel) -> Sample:
        """Convert ORM model to domain entity."""
        return Sample(
            id=model.id,
            patient_id=model.patient_id,  # type: ignore[arg-type]
            sample_code=model.sample_code,
            status=model.status,
            collection_date=model.collection_date,
            fastq_r1_path=model.fastq_r1_path,
            fastq_r2_path=model.fastq_r2_path,
            tsv_patients_path=model.tsv_patients_path,
            report_path=model.report_path,
            uploaded_at=model.uploaded_at,
            uploaded_by_id=model.uploaded_by_id,  # type: ignore[arg-type]
            processed_at=model.processed_at,
            annotated_at=model.annotated_at,
            annotated_by_id=model.annotated_by_id,  # type: ignore[arg-type]
            coverage_quality_passed=model.coverage_quality_passed,
            requires_resequencing=model.requires_resequencing,
            resequencing_requested_at=model.resequencing_requested_at,
            resequencing_requested_by_id=model.resequencing_requested_by_id,  # type: ignore[arg-type]
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Sample) -> SampleModel:
        """Convert domain entity to ORM model."""
        return SampleModel(
            id=entity.id,
            patient_id=entity.patient_id,
            sample_code=entity.sample_code,
            status=entity.status,
            collection_date=entity.collection_date,
            fastq_r1_path=entity.fastq_r1_path,
            fastq_r2_path=entity.fastq_r2_path,
            tsv_patients_path=entity.tsv_patients_path,
            report_path=entity.report_path,
            uploaded_at=entity.uploaded_at,
            uploaded_by_id=entity.uploaded_by_id,
            processed_at=entity.processed_at,
            annotated_at=entity.annotated_at,
            annotated_by_id=entity.annotated_by_id,
            coverage_quality_passed=entity.coverage_quality_passed,
            requires_resequencing=entity.requires_resequencing,
            resequencing_requested_at=entity.resequencing_requested_at,
            resequencing_requested_by_id=entity.resequencing_requested_by_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
