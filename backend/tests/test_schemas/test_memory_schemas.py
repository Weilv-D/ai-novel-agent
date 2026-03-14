"""Tests for memory schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.memory import (
    MemoryCreate,
    MemoryMatch,
    MemoryResponse,
    MemoryUpdate,
    VectorSearchRequest,
    VectorSearchResponse,
)

EMBEDDING_DIMENSION = get_settings().embedding_dimension


class TestMemorySchemas:
    """Tests for Memory schemas."""

    def test_memory_create_valid(self):
        """Test valid MemoryCreate schema."""
        project_id = uuid.uuid4()
        embedding = [0.1] * EMBEDDING_DIMENSION
        data = {
            "project_id": project_id,
            "memory_type": "episode",
            "content": "The hero defeated the dragon.",
            "embedding": embedding,
            "meta": {"chapter": 1, "characters": ["hero", "dragon"]},
        }
        schema = MemoryCreate(**data)
        assert schema.project_id == project_id
        assert schema.memory_type == "episode"
        assert schema.content == "The hero defeated the dragon."
        assert schema.embedding == embedding
        assert schema.meta["chapter"] == 1

    def test_memory_create_minimal(self):
        """Test MemoryCreate with minimal required fields."""
        project_id = uuid.uuid4()
        schema = MemoryCreate(
            project_id=project_id,
            memory_type="fact",
            content="The sword is made of mithril.",
        )
        assert schema.project_id == project_id
        assert schema.memory_type == "fact"
        assert schema.content == "The sword is made of mithril."
        assert schema.embedding is None
        assert schema.meta == {}

    def test_memory_create_without_embedding(self):
        """Test MemoryCreate without embedding (can be added later)."""
        project_id = uuid.uuid4()
        schema = MemoryCreate(
            project_id=project_id,
            memory_type="semantic",
            content="Magic requires concentration.",
        )
        assert schema.embedding is None

    def test_memory_update_partial(self):
        """Test MemoryUpdate with partial data."""
        data = {
            "content": "Updated memory content",
            "meta": {"verified": True},
        }
        schema = MemoryUpdate(**data)
        assert schema.content == "Updated memory content"
        assert schema.meta == {"verified": True}
        assert schema.memory_type is None
        assert schema.embedding is None

    def test_memory_update_with_embedding(self):
        """Test MemoryUpdate with new embedding."""
        embedding = [0.2] * EMBEDDING_DIMENSION
        data = {"embedding": embedding}
        schema = MemoryUpdate(**data)
        assert schema.embedding == embedding

    def test_memory_create_invalid_embedding_dimension(self):
        """Test MemoryCreate rejects embeddings with the wrong dimension."""
        project_id = uuid.uuid4()

        with pytest.raises(ValidationError) as exc_info:
            MemoryCreate(
                project_id=project_id,
                memory_type="episode",
                content="The hero defeated the dragon.",
                embedding=[0.1] * 8,
            )

        assert str(EMBEDDING_DIMENSION) in str(exc_info.value)

    def test_memory_response(self):
        """Test MemoryResponse schema."""
        memory_id = uuid.uuid4()
        project_id = uuid.uuid4()
        from datetime import datetime

        data = {
            "id": memory_id,
            "project_id": project_id,
            "memory_type": "episode",
            "content": "The battle ended at dawn.",
            "meta": {"location": "castle"},
            "embedding": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        schema = MemoryResponse(**data)
        assert schema.id == memory_id
        assert schema.project_id == project_id
        assert schema.memory_type == "episode"


class TestVectorSearchSchemas:
    """Tests for vector search schemas."""

    def test_vector_search_request_valid(self):
        """Test valid VectorSearchRequest schema."""
        embedding = [0.1] * EMBEDDING_DIMENSION
        data = {
            "query_embedding": embedding,
            "limit": 10,
            "threshold": 0.7,
            "memory_type": "episode",
        }
        schema = VectorSearchRequest(**data)
        assert schema.query_embedding == embedding
        assert schema.limit == 10
        assert schema.threshold == 0.7
        assert schema.memory_type == "episode"

    def test_vector_search_request_defaults(self):
        """Test VectorSearchRequest with default values."""
        embedding = [0.1] * EMBEDDING_DIMENSION
        schema = VectorSearchRequest(query_embedding=embedding)
        assert schema.limit == 10
        assert schema.threshold == 0.7
        assert schema.memory_type is None

    def test_vector_search_request_limit_validation(self):
        """Test limit validation (1-100)."""
        embedding = [0.1] * EMBEDDING_DIMENSION
        with pytest.raises(ValidationError):
            VectorSearchRequest(query_embedding=embedding, limit=0)

        with pytest.raises(ValidationError):
            VectorSearchRequest(query_embedding=embedding, limit=101)

    def test_vector_search_request_threshold_validation(self):
        """Test threshold validation (0.0-1.0)."""
        embedding = [0.1] * EMBEDDING_DIMENSION
        with pytest.raises(ValidationError):
            VectorSearchRequest(query_embedding=embedding, threshold=-0.1)

        with pytest.raises(ValidationError):
            VectorSearchRequest(query_embedding=embedding, threshold=1.1)

    def test_memory_match(self):
        """Test MemoryMatch schema."""
        memory_id = uuid.uuid4()
        data = {
            "id": memory_id,
            "memory_type": "fact",
            "content": "The door opens with a password.",
            "meta": {"location": "dungeon"},
            "similarity": 0.95,
        }
        schema = MemoryMatch(**data)
        assert schema.id == memory_id
        assert schema.similarity == 0.95

    def test_vector_search_response(self):
        """Test VectorSearchResponse schema."""
        memory_id = uuid.uuid4()
        matches = [
            {
                "id": memory_id,
                "memory_type": "fact",
                "content": "Test memory",
                "meta": {},
                "similarity": 0.85,
            }
        ]
        data = {
            "matches": matches,
            "total_count": 100,
            "search_summary": "Found 1 memories with similarity >= 0.7",
        }
        schema = VectorSearchResponse(**data)
        assert len(schema.matches) == 1
        assert schema.total_count == 100
        assert schema.search_summary == "Found 1 memories with similarity >= 0.7"
