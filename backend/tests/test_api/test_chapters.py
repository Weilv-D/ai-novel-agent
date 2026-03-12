"""Tests for Chapter/Scene/Volume API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chapter import ChapterResponse, SceneResponse, VolumeResponse


class TestVolumeRoutes:
    """Tests for Volume endpoints."""

    def test_list_volumes_by_project(self):
        """Test listing volumes for a project."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = VolumeResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            volume_number=1,
            title="Book One",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.chapters.volume_service.get_by_project", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/volumes/project/{project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["title"] == "Book One"


class TestChapterRoutes:
    """Tests for Chapter endpoints."""

    def test_list_chapters_by_project(self):
        """Test listing chapters for a project."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = ChapterResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            volume_id=None,
            chapter_number=1,
            title="Chapter One",
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.chapters.chapter_service.get_by_project", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/chapters/project/{project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["title"] == "Chapter One"

    def test_get_chapter_found(self):
        """Test getting a chapter by ID."""
        client = TestClient(app)
        chapter_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = ChapterResponse(
            id=chapter_id,
            project_id=project_id,
            volume_id=None,
            chapter_number=1,
            title="Chapter One",
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.chapters.chapter_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/chapters/{chapter_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(chapter_id)


class TestSceneRoutes:
    """Tests for Scene endpoints."""

    def test_list_scenes_by_chapter(self):
        """Test listing scenes for a chapter."""
        client = TestClient(app)
        chapter_id = uuid.uuid4()

        mock_response = SceneResponse(
            id=uuid.uuid4(),
            chapter_id=chapter_id,
            scene_order=1,
            location="Castle",
            content="The story begins...",
            meta={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.chapters.scene_service.get_by_chapter", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/scenes/chapter/{chapter_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["location"] == "Castle"

    def test_get_scene_found(self):
        """Test getting a scene by ID."""
        client = TestClient(app)
        scene_id = uuid.uuid4()
        chapter_id = uuid.uuid4()

        mock_response = SceneResponse(
            id=scene_id,
            chapter_id=chapter_id,
            scene_order=1,
            content="Scene content",
            meta={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.chapters.scene_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/scenes/{scene_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(scene_id)
