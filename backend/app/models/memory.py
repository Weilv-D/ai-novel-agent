"""Memory model for storing narrative facts and vector embeddings."""

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import Column, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID, VECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class MemoryType(str, Enum):
    """Types of memories."""

    EPISODE = "episode"  # Event summaries
    SEMANTIC = "semantic"  # World rules, character traits
    FACT = "fact"  # Specific facts that may be referenced


class Memory(Base, UUIDMixin, TimestampMixin):
    """Memory model for narrative facts with vector embeddings."""

    __tablename__ = "memories"

    # Foreign key to project
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Type of memory
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector embedding (1536 dimensions for OpenAI embeddings)
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(1536), nullable=True)

    # Metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"Memory(id={self.id!r}, type={self.memory_type!r}, content={self.content[:50]!r}...)"
