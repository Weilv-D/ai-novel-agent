"""Suggestion model for three-state modification system."""

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import Column, ForeignKey, JSON, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class SuggestionStatus(str, Enum):
    """Suggestion status values."""

    DRAFT = "draft"  # Initial AI suggestion
    PATCHED = "patched"  # User confirmed, awaiting impact analysis
    COMMITTED = "committed"  # Applied to target object
    DISCARDED = "discarded"  # User rejected


class SuggestionType(str, Enum):
    """Types of suggestions."""

    CHARACTER_EDIT = "character_edit"
    WORLD_EDIT = "world_edit"
    CHAPTER_EDIT = "chapter_edit"
    SCENE_EDIT = "scene_edit"
    CONTENT_GEN = "content_gen"
    OUTLINE_GEN = "outline_gen"
    CONTINUITY_FIX = "continuity_fix"


class Suggestion(Base, UUIDMixin, TimestampMixin):
    """Suggestion model for three-state modification system."""

    __tablename__ = "suggestions"

    # Foreign key to project
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Target of the suggestion
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # character, world_setting, chapter, scene
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Type of suggestion
    type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Content (JSONB for flexibility)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=SuggestionStatus.DRAFT.value, nullable=False, index=True
    )

    # Impact analysis results (populated when status=patched)
    impact_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # When committed
    committed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"Suggestion(id={self.id!r}, type={self.type!r}, status={self.status!r})"
