"""File record repository interface."""

from abc import abstractmethod
from uuid import UUID

from src.domain.entities import FileRecord
from src.domain.enums import FileType
from src.domain.repositories.base import IRepository


class IFileRecordRepository(IRepository[FileRecord]):
    """Repository interface for FileRecord entities."""

    @abstractmethod
    async def get_by_sample_id(
        self,
        sample_id: UUID,
        file_type: FileType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FileRecord]:
        """Get file records by sample ID, optionally filtered by file type.

        Args:
            sample_id: Sample UUID
            file_type: Optional file type filter
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of file records
        """
        ...

    @abstractmethod
    async def get_by_sample_and_type(
        self,
        sample_id: UUID,
        file_type: FileType,
    ) -> FileRecord | None:
        """Get file record by sample ID and file type.

        Args:
            sample_id: Sample UUID
            file_type: File type

        Returns:
            File record if found, None otherwise
        """
        ...

    @abstractmethod
    async def save_many(
        self,
        file_records: list[FileRecord],
    ) -> list[FileRecord]:
        """Save multiple file records in bulk.

        Args:
            file_records: List of file records to save

        Returns:
            List of saved file records
        """
        ...
