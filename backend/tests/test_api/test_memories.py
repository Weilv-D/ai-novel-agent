"""Tests for Memory API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.memory import MemoryResponse, MemoryMatch


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
            "embedding": [0.1] * 1536,
        }

        mock_response = MemoryResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            memory_type="semantic",
            content="Magic exists in this world.",
            meta={},
            embedding=[0.1] * 1536,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.memories.memory_service.create_with_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/memories", json=memory_data)

            assert response.status_code == status.HTTP_201_CREATED


class TestSearchMemoriesByEmbedding:
    """Tests for POST /api/v1/memories/search."""

    def test_search_memories_by_embedding(self):
        """Test vector similarity search for memories."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        search_request = {
            "query_embedding": [0.1] * 1536,
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
            "query_embedding": [0.1] * 1536,
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
