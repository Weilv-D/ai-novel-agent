"""Chapter and Scene models for novel structure."""

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Volume(Base, UUIDMixin, TimestampMixin):
    """Volume model (optional grouping of chapters)."""

    __tablename__ = "volumes"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    volume_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"Volume(id={self.id!r}, title={self.title!r}, volume_number={self.volume_number!r})"


class ChapterStatus(str, Enum):
    """Chapter status values."""

    DRAFT = "draft"
    WRITING = "writing"
    COMPLETED = "completed"


class Chapter(Base, UUIDMixin, TimestampMixin):
    """Chapter model."""

    __tablename__ = "chapters"

    # Foreign keys
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    volume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("volumes.id", ondelete="SET NULL"), nullable=True
    )

    # Chapter info
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outline: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Content (can be stored directly or via scenes)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default=ChapterStatus.DRAFT.value, nullable=False)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Constraints
    __table_args__ = (UniqueConstraint("project_id", "volume_id", "chapter_number", name="unique_chapter_number"),)

    def __repr__(self) -> str:
        return f"Chapter(id={self.id!r}, title={self.title!r}, number={self.chapter_number!r})"


class Scene(Base, UUIDMixin, TimestampMixin):
    """Scene model - the smallest unit of narrative."""

    __tablename__ = "scenes"

    # Foreign key
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Order within chapter
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Scene parameters
    pov_character_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Content
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSONB for extensibility (characters present, time, weather, etc.)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, name="metadata")

    def __repr__(self) -> str:
        return f"Scene(id={self.id!r}, chapter_id={self.chapter_id!r}, order={self.scene_order!r})"
