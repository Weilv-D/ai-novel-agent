"""Dependency model for impact analysis."""

import uuid
from typing import Any

from sqlalchemy import Column, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class DependencyType(str, Enum):
    """Types of dependencies."""

    REFERENCES = "references"  # e.g., chapter references character
    INFLUENCES = "influences"  # e.g., setting influences character
    CONTAINS = "contains"  # e.g., volume contains chapter
    PRECEDES = "precedes"  # e.g., chapter precedes another chapter


from enum import Enum


class Dependency(Base, UUIDMixin, TimestampMixin):
    """Dependency model for tracking relationships between objects."""

    __tablename__ = "dependencies"

    # Foreign key to project
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Source of dependency
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Target of dependency
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Type of dependency
    dependency_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "project_id", "source_type", "source_id", "target_type", "target_id", name="unique_dependency"
        ),
    )

    def __repr__(self) -> str:
        return f"Dependency(source={self.source_type}:{self.source_id} -> target={self.target_type}:{self.target_id})"
