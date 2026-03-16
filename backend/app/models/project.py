"""Project model - the main container for a novel."""

from enum import Enum
from typing import Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

DEFAULT_AGENT_PROFILE_ID = "default"


class ProjectStatus(str, Enum):
    """Project status values."""

    DRAFTING = "drafting"
    WRITING = "writing"
    REVISING = "revising"
    COMPLETED = "completed"


class Project(Base, UUIDMixin, TimestampMixin):
    """Project model representing a novel project."""

    __tablename__ = "projects"

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
    story_outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSONB for extensibility
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, name="metadata")

    @property
    def agent_profile_id(self) -> str:
        """Active agent profile for this project."""
        return str((self.meta or {}).get("agent_profile_id") or DEFAULT_AGENT_PROFILE_ID)

    @agent_profile_id.setter
    def agent_profile_id(self, value: str | None) -> None:
        """Persist the selected agent profile inside project metadata."""
        normalized = (value or DEFAULT_AGENT_PROFILE_ID).strip() or DEFAULT_AGENT_PROFILE_ID
        next_meta = dict(self.meta or {})
        next_meta["agent_profile_id"] = normalized
        self.meta = next_meta

    def __repr__(self) -> str:
        return f"Project(id={self.id!r}, name={self.name!r}, status={self.status!r})"
