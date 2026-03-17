"""Chapter and Scene schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.types import CONTENT_MAX_LENGTH, NOTES_MAX_LENGTH, OUTLINE_MAX_LENGTH, TargetTypeLiteral

# ============ Enums ============

ChapterStatusLiteral = Literal["draft", "writing", "completed"]

# ============ Volume Schemas ============

class VolumeBase(BaseModel):
    """Base volume schema."""

    volume_number: int | None = Field(None, ge=1)
    title: str | None = Field(None, max_length=255)
    outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH, description=f"Volume outline, max {OUTLINE_MAX_LENGTH} characters")
    notes: str | None = Field(None, max_length=NOTES_MAX_LENGTH, description=f"Volume notes, max {NOTES_MAX_LENGTH} characters")


class VolumeCreate(VolumeBase):
    """Schema for creating a volume."""

    project_id: UUID


class VolumeUpdate(BaseModel):
    """Schema for updating a volume."""

    volume_number: int | None = Field(None, ge=1)
    title: str | None = Field(None, max_length=255)
    outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH, description=f"Volume outline, max {OUTLINE_MAX_LENGTH} characters")
    notes: str | None = Field(None, max_length=NOTES_MAX_LENGTH, description=f"Volume notes, max {NOTES_MAX_LENGTH} characters")


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
    outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH, description=f"Chapter outline, max {OUTLINE_MAX_LENGTH} characters")
    content: str | None = Field(None, max_length=CONTENT_MAX_LENGTH, description=f"Chapter content, max {CONTENT_MAX_LENGTH} characters")
    status: ChapterStatusLiteral = Field(default="draft")
    notes: str | None = Field(None, max_length=NOTES_MAX_LENGTH, description=f"Chapter notes, max {NOTES_MAX_LENGTH} characters")


class ChapterCreate(ChapterBase):
    """Schema for creating a chapter."""

    project_id: UUID
    volume_id: UUID | None = None


class ChapterUpdate(BaseModel):
    """Schema for updating a chapter."""

    chapter_number: int | None = Field(None, ge=1)
    title: str | None = Field(None, max_length=255)
    outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH, description=f"Chapter outline, max {OUTLINE_MAX_LENGTH} characters")
    content: str | None = Field(None, max_length=CONTENT_MAX_LENGTH, description=f"Chapter content, max {CONTENT_MAX_LENGTH} characters")
    status: ChapterStatusLiteral | None = None
    notes: str | None = Field(None, max_length=NOTES_MAX_LENGTH, description=f"Chapter notes, max {NOTES_MAX_LENGTH} characters")
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
    content: str | None = Field(None, max_length=CONTENT_MAX_LENGTH, description=f"Scene content, max {CONTENT_MAX_LENGTH} characters")
    meta: dict[str, Any] = Field(default_factory=dict)


class SceneCreate(SceneBase):
    """Schema for creating a scene."""

    chapter_id: UUID


class SceneUpdate(BaseModel):
    """Schema for updating a scene."""

    scene_order: int | None = Field(None, ge=1)
    pov_character_id: UUID | None = None
    location: str | None = Field(None, max_length=255)
    content: str | None = Field(None, max_length=CONTENT_MAX_LENGTH, description=f"Scene content, max {CONTENT_MAX_LENGTH} characters")
    meta: dict[str, Any] | None = Field(None)


class SceneResponse(SceneBase):
    """Schema for scene response."""

    id: UUID
    chapter_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
