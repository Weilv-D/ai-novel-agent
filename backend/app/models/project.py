"""Project model - the main container for a novel."""

from enum import Enum
from typing import Any, cast

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

DEFAULT_AGENT_PROFILE_ID = "default"
DEFAULT_AGENT_SETTINGS: dict[str, Any] = {
    "style_goal": None,
    "tone_keywords": [],
    "voice_constraints": [],
    "forbidden_patterns": [],
    "terminology_glossary": [],
    "chapter_target_chars": 6000,
    "scene_target_chars": None,
    "continuity_mode": "strict",
}


def normalize_agent_settings(value: dict[str, Any] | None) -> dict[str, Any]:
    """Return a stable project-level agent settings payload."""
    raw = value or {}
    normalized = {
        "style_goal": str(raw.get("style_goal")).strip() if raw.get("style_goal") else None,
        "tone_keywords": [str(item).strip() for item in raw.get("tone_keywords", []) if str(item).strip()],
        "voice_constraints": [str(item).strip() for item in raw.get("voice_constraints", []) if str(item).strip()],
        "forbidden_patterns": [str(item).strip() for item in raw.get("forbidden_patterns", []) if str(item).strip()],
        "terminology_glossary": [str(item).strip() for item in raw.get("terminology_glossary", []) if str(item).strip()],
        "chapter_target_chars": raw.get("chapter_target_chars", DEFAULT_AGENT_SETTINGS["chapter_target_chars"]),
        "scene_target_chars": raw.get("scene_target_chars"),
        "continuity_mode": str(raw.get("continuity_mode") or DEFAULT_AGENT_SETTINGS["continuity_mode"]).strip()
        or DEFAULT_AGENT_SETTINGS["continuity_mode"],
    }
    if not isinstance(normalized["chapter_target_chars"], int) or cast(int, normalized["chapter_target_chars"]) <= 0:
        normalized["chapter_target_chars"] = DEFAULT_AGENT_SETTINGS["chapter_target_chars"]
    if normalized["scene_target_chars"] is not None and (
        not isinstance(normalized["scene_target_chars"], int) or cast(int, normalized["scene_target_chars"]) <= 0
    ):
        normalized["scene_target_chars"] = None
    if normalized["continuity_mode"] not in {"standard", "strict"}:
        normalized["continuity_mode"] = DEFAULT_AGENT_SETTINGS["continuity_mode"]
    return normalized


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

    @property
    def agent_settings(self) -> dict[str, Any]:
        """Project-level style and continuity controls used by the agent."""
        raw = (self.meta or {}).get("agent_settings")
        if not isinstance(raw, dict):
            return dict(DEFAULT_AGENT_SETTINGS)
        return normalize_agent_settings(raw)

    @agent_settings.setter
    def agent_settings(self, value: dict[str, Any] | None) -> None:
        """Persist normalized agent settings inside project metadata."""
        next_meta = dict(self.meta or {})
        next_meta["agent_settings"] = normalize_agent_settings(value)
        self.meta = next_meta

    def __repr__(self) -> str:
        return f"Project(id={self.id!r}, name={self.name!r}, status={self.status!r})"
