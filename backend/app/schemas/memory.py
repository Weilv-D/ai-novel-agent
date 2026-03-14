"""Memory schemas for narrative facts and vector embeddings."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings

EMBEDDING_DIMENSION = get_settings().embedding_dimension


def _validate_embedding_length(
    value: list[float] | None,
    *,
    field_name: str,
) -> list[float] | None:
    """Validate that an embedding matches the configured vector size."""
    if value is not None and len(value) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"{field_name} must have {EMBEDDING_DIMENSION} dimensions, got {len(value)}"
        )
    return value

# ============ Enums ============

# Type literals for memory types
MemoryTypeLiteral = str  # EPISODE, SEMANTIC, FACT


# Memory type constants for backward compatibility and convenience
class MemoryType:
    """Memory type constants."""

    EPISODE = "episode"  # Event summaries
    SEMANTIC = "semantic"  # World rules, character traits
    FACT = "fact"  # Specific facts that may be referenced


# ============ Memory Schemas ============


class MemoryBase(BaseModel):
    """Base memory schema."""

    memory_type: MemoryTypeLiteral = Field(
        ..., description="Type of memory (episode, semantic, fact)"
    )
    content: str = Field(..., description="Memory content text")
    meta: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class MemoryCreate(MemoryBase):
    """Schema for creating a memory."""

    project_id: UUID = Field(..., description="Project ID this memory belongs to")
    embedding: list[float] | None = Field(
        None,
        description=f"Vector embedding ({EMBEDDING_DIMENSION} dimensions)",
    )
    auto_embed: bool = Field(
        False, description="Automatically generate embedding from content"
    )

    @field_validator("embedding")
    @classmethod
    def validate_embedding(cls, value: list[float] | None) -> list[float] | None:
        """Validate embedding length when supplied explicitly."""
        return _validate_embedding_length(value, field_name="embedding")


class MemoryUpdate(BaseModel):
    """Schema for updating a memory."""

    content: str | None = None
    memory_type: MemoryTypeLiteral | None = None
    meta: dict[str, Any] | None = None
    embedding: list[float] | None = None
    auto_embed: bool | None = Field(
        False, description="Automatically regenerate embedding from content if content changes"
    )

    @field_validator("embedding")
    @classmethod
    def validate_embedding(cls, value: list[float] | None) -> list[float] | None:
        """Validate embedding length when supplied explicitly."""
        return _validate_embedding_length(value, field_name="embedding")


class MemoryResponse(MemoryBase):
    """Schema for memory response."""

    id: UUID
    project_id: UUID
    embedding: list[float] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============ Vector Search Schemas ============


class VectorSearchRequest(BaseModel):
    """Schema for vector similarity search request."""

    query_embedding: list[float] = Field(
        ..., description="Query vector embedding for similarity search"
    )
    limit: int = Field(
        10, ge=1, le=100, description="Maximum number of results to return"
    )
    threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity threshold (cosine)"
    )
    memory_type: MemoryTypeLiteral | None = Field(
        None, description="Optional filter by memory type"
    )

    @field_validator("query_embedding")
    @classmethod
    def validate_query_embedding(cls, value: list[float]) -> list[float]:
        """Validate search embedding length."""
        validated = _validate_embedding_length(value, field_name="query_embedding")
        return validated if validated is not None else value


class MemoryMatch(BaseModel):
    """A single memory match from vector search."""

    id: UUID
    memory_type: MemoryTypeLiteral
    content: str
    meta: dict[str, Any]
    similarity: float = Field(..., description="Cosine similarity score (0-1)")


class VectorSearchResponse(BaseModel):
    """Schema for vector search response."""

    matches: list[MemoryMatch]
    total_count: int
    search_summary: str | None = None
