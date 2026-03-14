"""Memory model for storing narrative facts and vector embeddings."""

import uuid
from enum import Enum
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.core.config import get_settings

# Import Vector type conditionally for SQLite compatibility
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback for SQLite testing: use a TypeDecorator that stores as JSON
    from sqlalchemy import TypeDecorator, TEXT
    import json

    class Vector(TypeDecorator):
        """Fallback Vector type for SQLite compatibility."""

        impl = TEXT
        cache_ok = True

        def __init__(self, dimension: int):
            super().__init__()
            self.dimension = dimension

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            return json.dumps(value)

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            return json.loads(value)


class MemoryType(str, Enum):
    """Types of memories."""

    EPISODE = "episode"  # Event summaries
    SEMANTIC = "semantic"  # World rules, character traits
    FACT = "fact"  # Specific facts that may be referenced


EMBEDDING_DIMENSION = get_settings().embedding_dimension


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

    # Vector embedding dimension is configured via EMBEDDING_DIMENSION.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)

    # Metadata
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, name="metadata")

    def __repr__(self) -> str:
        return f"Memory(id={self.id!r}, type={self.memory_type!r}, content={self.content[:50]!r}...)"
