"""Project schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=255)
    genre: str | None = Field(None, max_length=100)
    target_audience: str | None = Field(None, max_length=100)
    target_word_count: int | None = Field(None, ge=0)
    summary: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    status: str = "drafting"


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    genre: str | None = Field(None, max_length=100)
    target_audience: str | None = Field(None, max_length=100)
    target_word_count: int | None = Field(None, ge=0)
    status: str | None = None
    summary: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""

    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
