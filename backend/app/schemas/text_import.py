"""Schemas for structured text import."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.types import CONTENT_MAX_LENGTH, OUTLINE_MAX_LENGTH, SUMMARY_MAX_LENGTH
from app.schemas.world_setting import WorldSettingCategoryLiteral

TextImportPhaseLiteral = Literal[
    "structure_detection",
    "outline_extraction",
    "character_extraction",
    "world_setting_extraction",
    "completed",
    "error",
]


class TextImportProgress(BaseModel):
    """Streaming progress event emitted during import analysis."""

    phase: TextImportPhaseLiteral
    progress: float = Field(..., ge=0, le=1)
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class DetectedChapter(BaseModel):
    """Detected chapter preview."""

    chapter_number: int = Field(..., ge=1)
    title: str | None = Field(None, max_length=255)
    content: str = Field(..., max_length=CONTENT_MAX_LENGTH)
    outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH)
    content_length: int | None = Field(None, ge=0)
    content_truncated: bool = False


class DetectedVolume(BaseModel):
    """Detected volume preview."""

    volume_number: int = Field(..., ge=1)
    title: str | None = Field(None, max_length=255)
    outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH)
    chapter_numbers: list[int] = Field(default_factory=list)


class DetectedCharacter(BaseModel):
    """Detected character preview."""

    name: str = Field(..., min_length=1, max_length=255)
    role: str | None = Field(None, max_length=100)
    profile: dict[str, Any] = Field(default_factory=dict)
    relationships: dict[str, Any] = Field(default_factory=dict)


class DetectedWorldSetting(BaseModel):
    """Detected world-setting preview."""

    category: WorldSettingCategoryLiteral
    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=CONTENT_MAX_LENGTH)


class TextImportPreview(BaseModel):
    """Preview returned after text analysis and before commit."""

    preview_id: str | None = Field(None, min_length=1, max_length=64)
    compact_preview: bool = False
    project_name: str = Field(..., min_length=1, max_length=255)
    genre: str | None = Field(None, max_length=100)
    summary: str | None = Field(None, max_length=SUMMARY_MAX_LENGTH)
    story_outline: str | None = Field(None, max_length=OUTLINE_MAX_LENGTH)
    volumes: list[DetectedVolume] = Field(default_factory=list)
    chapters: list[DetectedChapter] = Field(default_factory=list)
    characters: list[DetectedCharacter] = Field(default_factory=list)
    world_settings: list[DetectedWorldSetting] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failed_phases: list[TextImportPhaseLiteral] = Field(default_factory=list)
    source_filename: str | None = Field(None, max_length=255)
    source_encoding: str | None = Field(None, max_length=60)


class TextImportConfirmRequest(BaseModel):
    """Request payload for confirming and committing an analyzed preview."""

    preview: TextImportPreview


class TextImportResponse(BaseModel):
    """Response returned after committing imported preview data."""

    project_id: UUID
    project_name: str
    imported_counts: dict[str, int]


TextImportJobStatusLiteral = Literal["queued", "processing", "completed", "failed"]


class TextImportJobResponse(BaseModel):
    """Background text-import job status payload."""

    id: UUID
    status: TextImportJobStatusLiteral
    phase: TextImportPhaseLiteral | None = None
    progress: float = Field(..., ge=0, le=1)
    message: str | None = None
    warnings: list[str] = Field(default_factory=list)
    failed_phases: list[TextImportPhaseLiteral] = Field(default_factory=list)
    preview: TextImportPreview | None = None
    error_detail: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
