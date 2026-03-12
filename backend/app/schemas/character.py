"""Character schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CharacterBase(BaseModel):
    """Base character schema."""

    name: str = Field(..., min_length=1, max_length=255)
    role: str | None = Field(None, max_length=100)
    profile: dict[str, Any] = Field(default_factory=dict)
    relationships: dict[str, Any] = Field(default_factory=dict)
    arc_state: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class CharacterCreate(CharacterBase):
    """Schema for creating a character."""

    project_id: UUID


class CharacterUpdate(BaseModel):
    """Schema for updating a character."""

    name: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, max_length=100)
    profile: dict[str, Any] | None = None
    relationships: dict[str, Any] | None = None
    arc_state: dict[str, Any] | None = None
    notes: str | None = None


class CharacterResponse(CharacterBase):
    """Schema for character response."""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
