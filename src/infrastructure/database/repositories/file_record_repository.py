"""File record repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import FileRecord
from src.domain.enums import FileType
from src.domain.repositories.file_record_repository import IFileRecordRepository
from src.infrastructure.database.models import FileRecordModel
from src.infrastructure.database.repositories.base import SQLAlchemyRepository


class SQLAlchemyFileRecordRepository(
    SQLAlchemyRepository[FileRecordModel, FileRecord],
    IFileRecordRepository,
):
    """SQLAlchemy implementation of FileRecord repository."""

    model_class = FileRecordModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_sample_id(
        self,
        sample_id: UUID,
        file_type: FileType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FileRecord]:
        """Get file records by sample ID, optionally filtered by file type."""
        stmt = (
            select(FileRecordModel)
            .where(FileRecordModel.sample_id == sample_id)
            .order_by(FileRecordModel.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if file_type:
            stmt = stmt.where(FileRecordModel.file_type == file_type)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_sample_and_type(
        self,
        sample_id: UUID,
        file_type: FileType,
    ) -> FileRecord | None:
        """Get file record by sample ID and file type."""
        stmt = select(FileRecordModel).where(
            FileRecordModel.sample_id == sample_id,
            FileRecordModel.file_type == file_type,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save_many(
        self,
        file_records: list[FileRecord],
    ) -> list[FileRecord]:
        """Save multiple file records in bulk."""
        models = [self._to_model(fr) for fr in file_records]
        self._session.add_all(models)
        await self._session.flush()
        for model in models:
            await self._session.refresh(model)
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: FileRecordModel) -> FileRecord:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return FileRecord(
            id=model.id,
            sample_id=UUID(str(model.sample_id)),  # Convert SQLAlchemy UUID to uuid.UUID
            file_type=model.file_type,
            file_path=model.file_path,
            file_name=model.file_name,
            file_size=model.file_size,
            checksum_md5=model.checksum_md5,
            uploaded_at=model.uploaded_at,
        )

    def _to_model(self, entity: FileRecord) -> FileRecordModel:
        """Convert domain entity to ORM model."""
        return FileRecordModel(
            id=entity.id,
            sample_id=entity.sample_id,
            file_type=entity.file_type,
            file_path=entity.file_path,
            file_name=entity.file_name,
            file_size=entity.file_size,
            checksum_md5=entity.checksum_md5,
            uploaded_at=entity.uploaded_at,
        )
