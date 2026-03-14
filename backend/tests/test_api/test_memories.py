"""Tests for Memory API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.schemas.memory import MemoryResponse

EMBEDDING_DIMENSION = get_settings().embedding_dimension


class TestListMemories:
    """Tests for GET /api/v1/memories."""

    def test_list_memories_empty(self):
        """Test listing memories when none exist."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch(
            "app.api.v1.memories.memory_service.get_by_project", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/memories?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []

    def test_list_memories_with_type_filter(self):
        """Test listing memories filtered by type."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = MemoryResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            memory_type="fact",
            content="A fact",
            meta={},
            embedding=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.memories.memory_service.get_by_project", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/memories?project_id={project_id}&memory_type=fact")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["memory_type"] == "fact"


class TestListMemoriesByType:
    """Tests for GET /api/v1/memories/type/{memory_type}."""

    def test_list_memories_by_type(self):
        """Test listing memories of a specific type."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = MemoryResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            memory_type="episode",
            content="An episode",
            meta={},
            embedding=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.memories.memory_service.get_by_type", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/memories/type/episode?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1


class TestCountMemories:
    """Tests for GET /api/v1/memories/count."""

    def test_count_memories(self):
        """Test counting memories for a project."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch(
            "app.api.v1.memories.memory_service.count_by_project", new_callable=AsyncMock
        ) as mock_count:
            mock_count.return_value = 5

            response = client.get(f"/api/v1/memories/count?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["count"] == 5
            assert data["project_id"] == str(project_id)

    def test_count_memories_by_type(self):
        """Test counting memories filtered by type."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch(
            "app.api.v1.memories.memory_service.count_by_project", new_callable=AsyncMock
        ) as mock_count:
            mock_count.return_value = 3

            response = client.get(
                f"/api/v1/memories/count?project_id={project_id}&memory_type=fact"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["count"] == 3
            assert data["memory_type"] == "fact"


class TestCreateMemory:
    """Tests for POST /api/v1/memories."""

    def test_create_memory_valid(self):
        """Test creating a memory with valid data."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        memory_data = {
            "project_id": str(project_id),
            "memory_type": "episode",
            "content": "The hero began their journey.",
            "meta": {"chapter": 1},
        }

        mock_response = MemoryResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            memory_type="episode",
            content="The hero began their journey.",
            meta={"chapter": 1},
            embedding=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.memories.memory_service.create_with_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/memories", json=memory_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["memory_type"] == "episode"

    def test_create_memory_with_embedding(self):
        """Test creating a memory with vector embedding."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        memory_data = {
            "project_id": str(project_id),
            "memory_type": "semantic",
            "content": "Magic exists in this world.",
            "embedding": [0.1] * EMBEDDING_DIMENSION,
        }

        mock_response = MemoryResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            memory_type="semantic",
            content="Magic exists in this world.",
            meta={},
            embedding=[0.1] * EMBEDDING_DIMENSION,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.memories.memory_service.create_with_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/memories", json=memory_data)

            assert response.status_code == status.HTTP_201_CREATED

    def test_create_memory_with_auto_embed(self):
        """Test creating a memory with auto-embed enabled."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        memory_data = {
            "project_id": str(project_id),
            "memory_type": "semantic",
            "content": "Magic exists in this world.",
            "auto_embed": True,
        }

        mock_embedding = [0.1] * EMBEDDING_DIMENSION

        mock_response = MemoryResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            memory_type="semantic",
            content="Magic exists in this world.",
            meta={},
            embedding=mock_embedding,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.memories.llm_service.embed_single", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.return_value = mock_embedding

            with patch(
                "app.api.v1.memories.memory_service.create_with_project", new_callable=AsyncMock
            ) as mock_create:
                mock_create.return_value = mock_response

                response = client.post("/api/v1/memories", json=memory_data)

                assert response.status_code == status.HTTP_201_CREATED
                mock_embed.assert_called_once_with("Magic exists in this world.")


class TestSearchMemoriesByEmbedding:
    """Tests for POST /api/v1/memories/search."""

    def test_search_memories_by_embedding(self):
        """Test vector similarity search for memories."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        search_request = {
            "query_embedding": [0.1] * EMBEDDING_DIMENSION,
            "limit": 10,
            "threshold": 0.7,
        }

        mock_match = {
            "id": uuid.uuid4(),
            "memory_type": "fact",
            "content": "A similar fact",
            "meta": {},
            "similarity": 0.85,
        }

        with patch(
            "app.api.v1.memories.memory_service.search_by_embedding", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = ([mock_match], 100)

            response = client.post(
                f"/api/v1/memories/search?project_id={project_id}", json=search_request
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "matches" in data
            assert len(data["matches"]) == 1
            assert data["matches"][0]["similarity"] == 0.85
            assert data["total_count"] == 100
            assert data["search_summary"] is not None

    def test_search_with_type_filter(self):
        """Test search with memory type filter."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        search_request = {
            "query_embedding": [0.1] * EMBEDDING_DIMENSION,
            "memory_type": "episode",
            "limit": 5,
        }

        with patch(
            "app.api.v1.memories.memory_service.search_by_embedding", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = ([], 0)

            response = client.post(
                f"/api/v1/memories/search?project_id={project_id}", json=search_request
            )

            assert response.status_code == status.HTTP_200_OK


class TestGetMemory:
    """Tests for GET /api/v1/memories/{id}."""

    def test_get_memory_found(self):
        """Test getting an existing memory."""
        client = TestClient(app)
        memory_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = MemoryResponse(
            id=memory_id,
            project_id=project_id,
            memory_type="fact",
            content="A fact",
            meta={},
            embedding=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.memories.memory_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/memories/{memory_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(memory_id)


class TestUpdateMemory:
    """Tests for PATCH /api/v1/memories/{id}."""

    def test_update_memory_valid(self):
        """Test updating a memory with valid data."""
        client = TestClient(app)
        memory_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = MemoryResponse(
            id=memory_id,
            project_id=project_id,
            memory_type="fact",
            content="Updated content",
            meta={},
            embedding=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.memories.memory_service.get", new_callable=AsyncMock) as mock_get:
            with patch(
                "app.api.v1.memories.memory_service.update", new_callable=AsyncMock
            ) as mock_update:
                mock_get.return_value = mock_response
                mock_update.return_value = mock_response

                response = client.patch(
                    f"/api/v1/memories/{memory_id}", json={"content": "Updated content"}
                )

                assert response.status_code == status.HTTP_200_OK

    def test_update_memory_with_auto_embed(self):
        """Test updating a memory with auto-embed enabled."""
        client = TestClient(app)
        memory_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = MemoryResponse(
            id=memory_id,
            project_id=project_id,
            memory_type="fact",
            content="Updated content",
            meta={},
            embedding=[0.2] * EMBEDDING_DIMENSION,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.memories.memory_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with patch(
                "app.api.v1.memories.llm_service.embed_single", new_callable=AsyncMock
            ) as mock_embed:
                mock_embed.return_value = [0.2] * EMBEDDING_DIMENSION

                with patch(
                    "app.api.v1.memories.memory_service.update", new_callable=AsyncMock
                ) as mock_update:
                    mock_update.return_value = mock_response

                    response = client.patch(
                        f"/api/v1/memories/{memory_id}",
                        json={"content": "Updated content", "auto_embed": True},
                    )

                    assert response.status_code == status.HTTP_200_OK
                    mock_embed.assert_called_once_with("Updated content")


class TestDeleteMemory:
    """Tests for DELETE /api/v1/memories/{id}."""

    def test_delete_memory_success(self):
        """Test deleting a memory successfully."""
        client = TestClient(app)
        memory_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = MemoryResponse(
            id=memory_id,
            project_id=project_id,
            memory_type="fact",
            content="A fact",
            meta={},
            embedding=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.memories.memory_service.delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/v1/memories/{memory_id}")

            assert response.status_code == status.HTTP_200_OK


class TestAutoEmbedBehavior:
    """Tests for auto_embed behavior in create/update operations."""

    def test_create_with_auto_embed_no_api_key_returns_400(self):
        """Test that auto_embed with no API key returns 400 Bad Request."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        # Mock the service to return successfully
        with patch("app.api.v1.memories.memory_service.create_with_project", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MemoryResponse(
                id=uuid.uuid4(),
                project_id=project_id,
                memory_type="fact",
                content="Test content",
                meta={},
                embedding=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # Mock llm_service to raise BadRequestException for missing API key
            with patch("app.api.v1.memories.llm_service.embed_single", new_callable=AsyncMock) as mock_embed:
                from app.core.exceptions import BadRequestException
                mock_embed.side_effect = BadRequestException("OpenAI API key not configured")

                response = client.post(
                    f"/api/v1/memories?project_id={project_id}",
                    json={
                        "project_id": str(project_id),
                        "memory_type": "fact",
                        "content": "Test content",
                        "auto_embed": True,
                    },
                )

                # Should return 400 for missing API key
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                data = response.json()
                assert "error" in data
                assert "API key" in data["error"]["message"]

    def test_create_with_auto_embed_service_failure_returns_503(self):
        """Test that auto_embed with service failure returns 503 Service Unavailable."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        # Mock llm_service to raise ServiceUnavailableException
        with patch("app.api.v1.memories.llm_service.embed_single", new_callable=AsyncMock) as mock_embed:
            from app.core.exceptions import ServiceUnavailableException
            mock_embed.side_effect = ServiceUnavailableException("Embedding service error: API timeout")

            response = client.post(
                f"/api/v1/memories?project_id={project_id}",
                json={
                    "project_id": str(project_id),
                    "memory_type": "fact",
                    "content": "Test content",
                    "auto_embed": True,
                },
            )

            # Should return 503 for service failure
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert "error" in data
            assert "service error" in data["error"]["message"].lower()

    def test_create_with_auto_embed_excludes_control_field_from_orm(self):
        """Test that auto_embed control field is not written to ORM via model_dump(exclude)."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        memory_id = uuid.uuid4()

        async def mock_create_with_project(db, *, obj_in, project_id):
            # Simulate what the real service does: model_dump with exclude
            obj_dict = obj_in.model_dump(exclude={"project_id", "auto_embed"})
            # Verify auto_embed is excluded from the dict that would create the ORM object
            assert "auto_embed" not in obj_dict, "auto_embed should be excluded from ORM creation"
            assert "project_id" not in obj_dict, "project_id should be excluded (passed separately)"
            # Return a response
            return MemoryResponse(
                id=memory_id,
                project_id=project_id,
                memory_type=obj_in.memory_type,
                content=obj_in.content,
                meta=obj_in.meta,
                embedding=obj_in.embedding,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

        with patch("app.api.v1.memories.memory_service.create_with_project", new=mock_create_with_project):
            # Mock successful embedding
            with patch("app.api.v1.memories.llm_service.embed_single", new_callable=AsyncMock) as mock_embed:
                mock_embed.return_value = [0.1] * EMBEDDING_DIMENSION

                response = client.post(
                    f"/api/v1/memories?project_id={project_id}",
                    json={
                        "project_id": str(project_id),
                        "memory_type": "fact",
                        "content": "Test content",
                        "auto_embed": True,
                    },
                )

                assert response.status_code == status.HTTP_201_CREATED

    def test_update_with_auto_embed_no_api_key_returns_400(self):
        """Test that update with auto_embed and no API key returns 400."""
        client = TestClient(app)
        memory_id = uuid.uuid4()

        # Mock the service get and update
        with patch("app.api.v1.memories.memory_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MemoryResponse(
                id=memory_id,
                project_id=uuid.uuid4(),
                memory_type="fact",
                content="Old content",
                meta={},
                embedding=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            with patch("app.api.v1.memories.memory_service.update", new_callable=AsyncMock) as mock_update:
                mock_update.return_value = mock_get.return_value

                # Mock llm_service to raise BadRequestException
                with patch("app.api.v1.memories.llm_service.embed_single", new_callable=AsyncMock) as mock_embed:
                    from app.core.exceptions import BadRequestException
                    mock_embed.side_effect = BadRequestException("OpenAI API key not configured")

                    response = client.patch(
                        f"/api/v1/memories/{memory_id}",
                        json={
                            "content": "New content",
                            "auto_embed": True,
                        },
                    )

                    assert response.status_code == status.HTTP_400_BAD_REQUEST
                    data = response.json()
                    assert "error" in data
                    assert "API key" in data["error"]["message"]

    def test_create_without_auto_embed_skips_embedding(self):
        """Test that create without auto_embed skips embedding generation."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch("app.api.v1.memories.memory_service.create_with_project", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MemoryResponse(
                id=uuid.uuid4(),
                project_id=project_id,
                memory_type="fact",
                content="Test content",
                meta={},
                embedding=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            with patch("app.api.v1.memories.llm_service.embed_single", new_callable=AsyncMock) as mock_embed:
                response = client.post(
                    f"/api/v1/memories?project_id={project_id}",
                    json={
                        "project_id": str(project_id),
                        "memory_type": "fact",
                        "content": "Test content",
                        "auto_embed": False,
                    },
                )

                assert response.status_code == status.HTTP_201_CREATED
                # Embed service should not be called when auto_embed is False
                mock_embed.assert_not_called()

    def test_create_with_provided_embedding_skips_auto_embed(self):
        """Test that providing embedding directly skips auto-embed even if True."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        provided_embedding = [0.5] * EMBEDDING_DIMENSION

        with patch("app.api.v1.memories.memory_service.create_with_project", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MemoryResponse(
                id=uuid.uuid4(),
                project_id=project_id,
                memory_type="fact",
                content="Test content",
                meta={},
                embedding=provided_embedding,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            with patch("app.api.v1.memories.llm_service.embed_single", new_callable=AsyncMock) as mock_embed:
                response = client.post(
                    f"/api/v1/memories?project_id={project_id}",
                    json={
                        "project_id": str(project_id),
                        "memory_type": "fact",
                        "content": "Test content",
                        "embedding": provided_embedding,
                        "auto_embed": True,  # Should be ignored since embedding is provided
                    },
                )

                assert response.status_code == status.HTTP_201_CREATED
                # Should not call embed_single when embedding is already provided
                mock_embed.assert_not_called()
