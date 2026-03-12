"""Snapshot model for version control and rollback."""

import uuid
from typing import Any

from sqlalchemy import Column, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Snapshot(Base, UUIDMixin, TimestampMixin):
    """Snapshot model for object version control."""

    __tablename__ = "snapshots"

    # Foreign key to project
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Target of snapshot
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # character, world_setting, chapter, etc.
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Snapshot data (JSON representation of the object)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    def __repr__(self) -> str:
        return f"Snapshot(id={self.id!r}, target_type={self.target_type!r}, target_id={self.target_id!r})"
