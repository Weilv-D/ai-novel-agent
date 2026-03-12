"""WorldSetting model for world-building elements."""

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorldSettingCategory(str, Enum):
    """Categories of world settings."""

    MAGIC_SYSTEM = "magic_system"
    GEOGRAPHY = "geography"
    HISTORY = "history"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    CULTURE = "culture"
    RELIGION = "religion"
    ECONOMY = "economy"
    RULES = "rules"
    OTHER = "other"


class WorldSetting(Base, UUIDMixin, TimestampMixin):
    """WorldSetting model for world-building elements."""

    __tablename__ = "world_settings"

    # Foreign key to project
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Categorization
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Content
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSONB for extensibility
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, name="metadata")

    def __repr__(self) -> str:
        return f"WorldSetting(id={self.id!r}, name={self.name!r}, category={self.category!r})"
