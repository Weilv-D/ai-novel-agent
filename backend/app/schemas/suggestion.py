"""Suggestion schemas for three-state modification system."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ============ Enums ============

# Status literals for suggestions
SuggestionStatusLiteral = Literal["draft", "patched", "committed", "discarded"]

# Type literals for suggestions
SuggestionTypeLiteral = Literal[
    "character_edit",
    "world_edit",
    "chapter_edit",
    "scene_edit",
    "content_gen",
    "outline_gen",
    "continuity_fix",
]

# Target type literals
TargetTypeLiteral = Literal["character", "world_setting", "chapter", "scene"]

# Action literals
SuggestionActionLiteral = Literal["confirm", "discard", "commit"]

# Status constants for backward compatibility and convenience
class SuggestionStatus:
    """Suggestion status constants."""

    DRAFT = "draft"
    PATCHED = "patched"
    COMMITTED = "committed"
    DISCARDED = "discarded"


class SuggestionType:
    """Suggestion type constants."""

    CHARACTER_EDIT = "character_edit"
    WORLD_EDIT = "world_edit"
    CHAPTER_EDIT = "chapter_edit"
    SCENE_EDIT = "scene_edit"
    CONTENT_GEN = "content_gen"
    OUTLINE_GEN = "outline_gen"
    CONTINUITY_FIX = "continuity_fix"


class SuggestionAction:
    """Suggestion action constants."""

    CONFIRM = "confirm"
    DISCARD = "discard"
    COMMIT = "commit"


# ============ Suggestion Schemas ============

class SuggestionBase(BaseModel):
    """Base suggestion schema."""

    target_type: TargetTypeLiteral = Field(
        ..., description="Type of target object (character, world_setting, chapter, scene)"
    )
    target_id: UUID = Field(..., description="ID of the target object")
    type: SuggestionTypeLiteral = Field(..., description="Type of suggestion")
    content: dict[str, Any] = Field(..., description="Suggestion content (JSON)")


class SuggestionCreate(SuggestionBase):
    """Schema for creating a suggestion."""

    project_id: UUID
    status: SuggestionStatusLiteral = Field(default="draft")


class SuggestionUpdate(BaseModel):
    """Schema for updating a suggestion.

    Note: Only 'content' can be updated via PATCH. Status changes must go through
    the confirm/discard/commit actions to ensure proper state transitions.
    """

    content: dict[str, Any] | None = None


class SuggestionResponse(SuggestionBase):
    """Schema for suggestion response."""

    id: UUID
    project_id: UUID
    status: SuggestionStatusLiteral
    impact_analysis: dict[str, Any] | None
    committed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============ Suggestion Action Schemas ============

class SuggestionActionRequest(BaseModel):
    """Schema for suggestion actions (confirm, discard, commit)."""

    action: SuggestionActionLiteral = Field(
        ..., description="Action to perform: confirm, discard, or commit"
    )
    impact_analysis: dict[str, Any] | None = Field(
        None, description="Impact analysis results (required for commit)"
    )


class SuggestionActionResult(BaseModel):
    """Schema for action result."""

    success: bool
    message: str
    suggestion_id: UUID
    action: SuggestionActionLiteral
