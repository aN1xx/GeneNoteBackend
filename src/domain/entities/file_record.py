"""File record entity."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from src.domain.enums import FileType


@dataclass
class FileRecord:
    """Domain entity representing a file in the system."""

    sample_id: UUID
    file_type: FileType
    file_path: str
    file_name: str
    id: UUID = field(default_factory=uuid4)
    file_size: int = 0
    checksum_md5: str | None = None
    uploaded_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate file record data."""
        if not self.file_path:
            msg = "File path cannot be empty"
            raise ValueError(msg)
        if not self.file_name:
            msg = "File name cannot be empty"
            raise ValueError(msg)

    @property
    def extension(self) -> str:
        """Get file extension."""
        path = Path(self.file_name)
        # Handle double extensions like .fastq.gz
        if path.suffix == ".gz" and path.stem.endswith(".fastq"):
            return ".fastq.gz"
        return path.suffix

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Get file size in gigabytes."""
        return self.file_size / (1024 * 1024 * 1024)

    def format_size(self) -> str:
        """Format file size for display."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        if self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        if self.file_size < 1024 * 1024 * 1024:
            return f"{self.size_mb:.1f} MB"
        return f"{self.size_gb:.2f} GB"

    def is_valid_extension(self) -> bool:
        """Check if file extension matches expected type."""
        expected = self.file_type.get_extension()
        return self.extension.lower() == expected.lower()
