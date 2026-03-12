"""Suggestion schemas for three-state modification system."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============ Enums ============

class SuggestionStatus(str):
    """Suggestion status values."""

    DRAFT = "draft"
    PATCHED = "patched"
    COMMITTED = "committed"
    DISCARDED = "discarded"


class SuggestionType(str):
    """Types of suggestions."""

    CHARACTER_EDIT = "character_edit"
    WORLD_EDIT = "world_edit"
    CHAPTER_EDIT = "chapter_edit"
    SCENE_EDIT = "scene_edit"
    CONTENT_GEN = "content_gen"
    OUTLINE_GEN = "outline_gen"
    CONTINUITY_FIX = "continuity_fix"


# ============ Suggestion Schemas ============

class SuggestionBase(BaseModel):
    """Base suggestion schema."""

    target_type: str = Field(..., description="Type of target object (character, world_setting, chapter, scene)")
    target_id: UUID = Field(..., description="ID of the target object")
    type: str = Field(..., description="Type of suggestion")
    content: dict[str, Any] = Field(..., description="Suggestion content (JSON)")


class SuggestionCreate(SuggestionBase):
    """Schema for creating a suggestion."""

    project_id: UUID
    status: str = Field(default=SuggestionStatus.DRAFT)


class SuggestionUpdate(BaseModel):
    """Schema for updating a suggestion."""

    content: dict[str, Any] | None = None
    status: str | None = None
    impact_analysis: dict[str, Any] | None = None


class SuggestionResponse(SuggestionBase):
    """Schema for suggestion response."""

    id: UUID
    project_id: UUID
    status: str
    impact_analysis: dict[str, Any] | None
    committed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============ Suggestion Action Schemas ============

class SuggestionActionRequest(BaseModel):
    """Schema for suggestion actions (confirm, discard, commit)."""

    action: str = Field(..., description="Action to perform: confirm, discard, or commit")
    impact_analysis: dict[str, Any] | None = Field(None, description="Impact analysis results (required for commit)")


class SuggestionActionResult(BaseModel):
    """Schema for action result."""

    success: bool
    message: str
    suggestion_id: UUID
    action: str
