"""Schemas for project timeline views."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TimelineVolumeInfo(BaseModel):
    """Compact volume metadata for timeline chapters."""

    id: UUID
    volume_number: int | None = None
    title: str | None = None


class TimelineEventResponse(BaseModel):
    """One event-memory item attached to the timeline."""

    id: UUID
    memory_type: str
    title: str
    summary: str
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)
    chapter_id: UUID | None = None
    chapter_number: int | None = None
    chapter_title: str | None = None
    scene_id: UUID | None = None
    scene_order: int | None = None
    location: str | None = None
    created_at: datetime
    updated_at: datetime


class TimelineChapterResponse(BaseModel):
    """One ordered chapter lane in the project timeline."""

    id: UUID
    volume: TimelineVolumeInfo | None = None
    chapter_number: int
    title: str | None = None
    status: str
    outline: str | None = None
    event_count: int = 0
    events: list[TimelineEventResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TimelineResponse(BaseModel):
    """Aggregated project timeline payload."""

    project_id: UUID
    chapters: list[TimelineChapterResponse] = Field(default_factory=list)
    unassigned_events: list[TimelineEventResponse] = Field(default_factory=list)
    total_events: int = 0
