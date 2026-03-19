"""Project schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.project import DEFAULT_AGENT_PROFILE_ID
from app.schemas.agent import AgentRunResponse, AgentThreadCheckpointResponse, AgentThreadResponse
from app.schemas.types import NOTES_MAX_LENGTH, OUTLINE_MAX_LENGTH, SUMMARY_MAX_LENGTH

# ============ Enums ============

ProjectStatusLiteral = Literal["drafting", "writing", "revising", "completed"]
ContinuityModeLiteral = Literal["standard", "strict"]


# ============ Status Constants ============

class ProjectStatus:
    """Project status constants."""

    DRAFTING = "drafting"
    WRITING = "writing"
    REVISING = "revising"
    COMPLETED = "completed"


class ProjectAgentSettings(BaseModel):
    """Project-level quality and style controls for the agent workflow."""

    style_goal: str | None = None
    tone_keywords: list[str] = Field(default_factory=list)
    voice_constraints: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    terminology_glossary: list[str] = Field(default_factory=list)
    chapter_target_chars: int | None = Field(default=6000, ge=1)
    scene_target_chars: int | None = Field(default=None, ge=1)
    continuity_mode: ContinuityModeLiteral = Field(default="strict")


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=255)
    genre: str | None = Field(None, max_length=100)
    target_audience: str | None = Field(None, max_length=100)
    target_word_count: int | None = Field(None, ge=0)
    summary: str | None = Field(None, max_length=SUMMARY_MAX_LENGTH, description=f"Project summary, max {SUMMARY_MAX_LENGTH} characters")
    story_outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH, description=f"Story outline, max {OUTLINE_MAX_LENGTH} characters")
    notes: str | None = Field(None, max_length=NOTES_MAX_LENGTH, description=f"Project notes, max {NOTES_MAX_LENGTH} characters")
    agent_profile_id: str = Field(default=DEFAULT_AGENT_PROFILE_ID, min_length=1, max_length=80)
    agent_settings: ProjectAgentSettings = Field(default_factory=ProjectAgentSettings)
    meta: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    status: ProjectStatusLiteral = Field(default="drafting")


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    genre: str | None = Field(None, max_length=100)
    target_audience: str | None = Field(None, max_length=100)
    target_word_count: int | None = Field(None, ge=0)
    status: ProjectStatusLiteral | None = None
    summary: str | None = Field(None, max_length=SUMMARY_MAX_LENGTH, description=f"Project summary, max {SUMMARY_MAX_LENGTH} characters")
    story_outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH, description=f"Story outline, max {OUTLINE_MAX_LENGTH} characters")
    notes: str | None = Field(None, max_length=NOTES_MAX_LENGTH, description=f"Project notes, max {NOTES_MAX_LENGTH} characters")
    agent_profile_id: str | None = Field(None, min_length=1, max_length=80)
    agent_settings: ProjectAgentSettings | None = None
    meta: dict[str, Any] | None = Field(None)


class ProjectResponse(ProjectBase):
    """Schema for project response."""

    id: UUID
    status: ProjectStatusLiteral
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class ProjectTreeSceneResponse(BaseModel):
    """Minimal scene entry used by project tree/workspace responses."""

    id: UUID
    chapter_id: UUID
    scene_order: int
    location: str | None = None
    pov_character_id: UUID | None = None

    model_config = {"from_attributes": True}


class ProjectTreeChapterResponse(BaseModel):
    """Minimal chapter node with nested scenes."""

    id: UUID
    project_id: UUID
    volume_id: UUID | None = None
    chapter_number: int
    title: str | None = None
    outline: str | None = None
    status: str
    scenes: list[ProjectTreeSceneResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProjectTreeVolumeResponse(BaseModel):
    """Minimal volume node with nested chapters."""

    id: UUID
    project_id: UUID
    volume_number: int | None = None
    title: str | None = None
    outline: str | None = None
    chapters: list[ProjectTreeChapterResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProjectTreeResponse(BaseModel):
    """Hierarchy used by the workspace navigator."""

    project_id: UUID
    volumes: list[ProjectTreeVolumeResponse] = Field(default_factory=list)
    ungrouped_chapters: list[ProjectTreeChapterResponse] = Field(default_factory=list)


class ProjectWorkspaceSummaryResponse(BaseModel):
    """Small workspace summary shown in the project workspace."""

    volume_count: int = 0
    chapter_count: int = 0
    scene_count: int = 0
    character_count: int = 0
    world_setting_count: int = 0
    latest_run_status: str | None = None
    context_source: str = "live_context"


class ProjectWorkspaceResponse(BaseModel):
    """Aggregated project workspace payload."""

    project: ProjectResponse
    agent_settings: ProjectAgentSettings
    tree: ProjectTreeResponse
    default_thread: AgentThreadResponse | None = None
    latest_checkpoint: AgentThreadCheckpointResponse | None = None
    current_run: AgentRunResponse | None = None
    recent_runs: list[AgentRunResponse] = Field(default_factory=list)
    workspace_summary: ProjectWorkspaceSummaryResponse
