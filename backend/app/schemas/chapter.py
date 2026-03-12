"""Chapter and Scene schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ============ Enums ============

ChapterStatusLiteral = Literal["draft", "writing", "completed"]
TargetTypeLiteral = Literal["character", "world_setting", "chapter", "scene"]

# ============ Volume Schemas ============

class VolumeBase(BaseModel):
    """Base volume schema."""

    volume_number: int | None = None
    title: str | None = Field(None, max_length=255)
    outline: str | None = None
    notes: str | None = None


class VolumeCreate(VolumeBase):
    """Schema for creating a volume."""

    project_id: UUID


class VolumeUpdate(BaseModel):
    """Schema for updating a volume."""

    volume_number: int | None = None
    title: str | None = Field(None, max_length=255)
    outline: str | None = None
    notes: str | None = None


class VolumeResponse(VolumeBase):
    """Schema for volume response."""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ============ Chapter Schemas ============

# Status constants for backward compatibility and convenience
class ChapterStatus:
    """Chapter status constants."""

    DRAFT = "draft"
    WRITING = "writing"
    COMPLETED = "completed"


class ChapterBase(BaseModel):
    """Base chapter schema."""

    chapter_number: int = Field(..., ge=1)
    title: str | None = Field(None, max_length=255)
    outline: str | None = None
    content: str | None = None
    status: ChapterStatusLiteral = Field(default=ChapterStatus.DRAFT)
    notes: str | None = None


class ChapterCreate(ChapterBase):
    """Schema for creating a chapter."""

    project_id: UUID
    volume_id: UUID | None = None


class ChapterUpdate(BaseModel):
    """Schema for updating a chapter."""

    chapter_number: int | None = Field(None, ge=1)
    title: str | None = Field(None, max_length=255)
    outline: str | None = None
    content: str | None = None
    status: ChapterStatusLiteral | None = None
    notes: str | None = None
    volume_id: UUID | None = None


class ChapterResponse(ChapterBase):
    """Schema for chapter response."""

    id: UUID
    project_id: UUID
    volume_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ============ Scene Schemas ============

class SceneBase(BaseModel):
    """Base scene schema."""

    scene_order: int = Field(..., ge=1)
    pov_character_id: UUID | None = None
    location: str | None = Field(None, max_length=255)
    content: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class SceneCreate(SceneBase):
    """Schema for creating a scene."""

    chapter_id: UUID


class SceneUpdate(BaseModel):
    """Schema for updating a scene."""

    scene_order: int | None = Field(None, ge=1)
    pov_character_id: UUID | None = None
    location: str | None = Field(None, max_length=255)
    content: str | None = None
    meta: dict[str, Any] | None = Field(None, alias="metadata")


class SceneResponse(SceneBase):
    """Schema for scene response."""

    id: UUID
    chapter_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
