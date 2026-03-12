"""Project schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ============ Enums ============

ProjectStatusLiteral = Literal["drafting", "writing", "revising", "completed"]


# ============ Status Constants ============

class ProjectStatus:
    """Project status constants."""

    DRAFTING = "drafting"
    WRITING = "writing"
    REVISING = "revising"
    COMPLETED = "completed"


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=255)
    genre: str | None = Field(None, max_length=100)
    target_audience: str | None = Field(None, max_length=100)
    target_word_count: int | None = Field(None, ge=0)
    summary: str | None = None
    notes: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    status: ProjectStatusLiteral = Field(default=ProjectStatus.DRAFTING)


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    genre: str | None = Field(None, max_length=100)
    target_audience: str | None = Field(None, max_length=100)
    target_word_count: int | None = Field(None, ge=0)
    status: ProjectStatusLiteral | None = None
    summary: str | None = None
    notes: str | None = None
    meta: dict[str, Any] | None = Field(None, alias="metadata")


class ProjectResponse(ProjectBase):
    """Schema for project response."""

    id: UUID
    user_id: UUID
    status: ProjectStatusLiteral
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
