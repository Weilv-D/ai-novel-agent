"""Character model for novel characters."""

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Character(Base, UUIDMixin, TimestampMixin):
    """Character model representing a character in a novel."""

    __tablename__ = "characters"

    # Foreign key to project
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)  # protagonist, antagonist, etc.

    # Character data stored as JSONB for flexibility
    profile: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )  # appearance, personality, background, etc.
    relationships: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )  # relationship network
    arc_state: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )  # character arc progression

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"Character(id={self.id!r}, name={self.name!r}, project_id={self.project_id!r})"
