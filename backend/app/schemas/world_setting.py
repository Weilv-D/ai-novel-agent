"""WorldSetting schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorldSettingBase(BaseModel):
    """Base world setting schema."""

    category: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorldSettingCreate(WorldSettingBase):
    """Schema for creating a world setting."""

    project_id: UUID


class WorldSettingUpdate(BaseModel):
    """Schema for updating a world setting."""

    category: str | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None
    metadata: dict[str, Any] | None = None


class WorldSettingResponse(WorldSettingBase):
    """Schema for world setting response."""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
