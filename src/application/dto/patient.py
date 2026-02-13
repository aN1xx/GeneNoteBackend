"""Patient DTOs."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.enums import Sex


class CreatePatientRequest(BaseModel):
    """Create patient request DTO."""

    name: str = Field(min_length=2, max_length=255)
    sex: Sex
    birth_date: date
    request_id: str = Field(min_length=1, max_length=50)
    analysis_name: str = Field(min_length=1)
    analysis_date: date | None = None


class UpdatePatientRequest(BaseModel):
    """Update patient request DTO."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    sex: Sex | None = None
    birth_date: date | None = None
    analysis_name: str | None = None
    analysis_date: date | None = None


class PatientResponse(BaseModel):
    """Patient response DTO."""

    id: UUID
    name: str
    sex: Sex
    birth_date: date
    request_id: str
    analysis_name: str
    analysis_date: date | None
    age: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    """Patient list response DTO with pagination."""

    items: list[PatientResponse]
    total: int
    limit: int
    offset: int


class PatientSearchRequest(BaseModel):
    """Patient search request DTO."""

    name: str | None = None
    request_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
