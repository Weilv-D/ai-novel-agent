"""Project model - the main container for a novel."""

import datetime
import uuid
from enum import Enum
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ProjectStatus(str, Enum):
    """Project status values."""

    DRAFTING = "drafting"
    WRITING = "writing"
    REVISING = "revising"
    COMPLETED = "completed"


class Project(Base, UUIDMixin, TimestampMixin):
    """Project model representing a novel project."""

    __tablename__ = "projects"

    # Foreign key to user (owner)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=ProjectStatus.DRAFTING.value, nullable=False
    )

    # Content fields
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSONB for extensibility
    metadata: Mapped[dict[str, Any]] = mapped_column(Column(JSON, default=dict, nullable=False))

    def __repr__(self) -> str:
        return f"Project(id={self.id!r}, name={self.name!r}, status={self.status!r})"
