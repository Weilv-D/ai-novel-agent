"""
HTTP Integration Tests for AI Novel Agent API.

Tests all API endpoints using real SQLite database and HTTP requests.
This is the pytest version of verify_sqlite_integration.py, providing
automated end-to-end testing without external dependencies.

Run with:
    pytest tests/test_integration/test_http_integration.py -v
"""

import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.core.security import get_password_hash


class TestHealthEndpoint:
    """Tests for /api/v1/health endpoint."""

    async def test_health_endpoint(self, client: AsyncClient) -> None:
        """Test health check returns correct status."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestProjectsAPI:
    """Tests for Projects API endpoints."""

    async def test_list_projects_empty(self, client: AsyncClient) -> None:
        """Test listing projects when none exist."""
        response = await client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        # Response can be empty list or dict with total/items
        if isinstance(data, dict):
            assert data["total"] == 0
            assert data["items"] == []
        else:
            assert data == []

    async def test_create_project(self, client: AsyncClient) -> None:
        """Test creating a new project."""
        project_data = {
            "name": "Integration Test Project",
            "genre": "fiction"
        }
        response = await client.post("/api/v1/projects", json=project_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["name"] == "Integration Test Project"
        assert data["genre"] == "fiction"

    async def test_get_project_by_id(self, client: AsyncClient) -> None:
        """Test getting a project by ID."""
        # First create a project
        project_data = {
            "name": "Test Project for Get",
            "genre": "fantasy"
        }
        create_response = await client.post("/api/v1/projects", json=project_data)
        assert create_response.status_code in (200, 201)
        project_id = create_response.json()["id"]

        # Get the project
        response = await client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Test Project for Get"

    async def test_update_project(self, client: AsyncClient) -> None:
        """Test updating a project."""
        # Create a project
        project_data = {
            "name": "Project to Update",
            "genre": "fiction"
        }
        create_response = await client.post("/api/v1/projects", json=project_data)
        project_id = create_response.json()["id"]

        # Update the project
        update_data = {"genre": "fantasy"}
        response = await client.patch(f"/api/v1/projects/{project_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["genre"] == "fantasy"


class TestCharactersAPI:
    """Tests for Characters API endpoints."""

    async def test_list_characters_empty(self, client: AsyncClient) -> None:
        """Test listing characters when none exist."""
        # Need a project first
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        response = await client.get(f"/api/v1/characters/project/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_create_character(self, client: AsyncClient) -> None:
        """Test creating a new character."""
        # Create a project first
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        character_data = {
            "project_id": project_id,
            "name": "Test Character",
            "role": "protagonist",
            "profile": {
                "personality": "Brave and curious",
                "appearance": "Tall with dark hair"
            }
        }
        response = await client.post("/api/v1/characters", json=character_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Character"
        assert data["role"] == "protagonist"

    async def test_get_character_by_id(self, client: AsyncClient) -> None:
        """Test getting a character by ID."""
        # Create project and character
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        character_data = {
            "project_id": project_id,
            "name": "Character for Get",
            "role": "protagonist"
        }
        create_response = await client.post("/api/v1/characters", json=character_data)
        character_id = create_response.json()["id"]

        # Get the character
        response = await client.get(f"/api/v1/characters/{character_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == character_id
        assert data["name"] == "Character for Get"

    async def test_update_character(self, client: AsyncClient) -> None:
        """Test updating a character."""
        # Create project and character
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        character_data = {
            "project_id": project_id,
            "name": "Character to Update",
            "role": "protagonist"
        }
        create_response = await client.post("/api/v1/characters", json=character_data)
        character_id = create_response.json()["id"]

        # Update the character
        update_data = {"role": "antagonist"}
        response = await client.patch(f"/api/v1/characters/{character_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "antagonist"

    async def test_delete_character(self, client: AsyncClient) -> None:
        """Test deleting a character."""
        # Create project and character
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        character_data = {
            "project_id": project_id,
            "name": "Character to Delete",
            "role": "protagonist"
        }
        create_response = await client.post("/api/v1/characters", json=character_data)
        character_id = create_response.json()["id"]

        # Delete the character
        response = await client.delete(f"/api/v1/characters/{character_id}")

        assert response.status_code in (200, 204)


class TestChaptersAPI:
    """Tests for Chapters API endpoints."""

    async def test_list_chapters_empty(self, client: AsyncClient) -> None:
        """Test listing chapters when none exist."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        response = await client.get(f"/api/v1/chapters/project/{project_id}")

        assert response.status_code == 200
        data = response.json()
        if isinstance(data, dict):
            assert data["total"] == 0
        else:
            assert len(data) == 0

    async def test_create_chapter(self, client: AsyncClient) -> None:
        """Test creating a new chapter."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Test Chapter",
            "status": "draft"
        }
        response = await client.post("/api/v1/chapters", json=chapter_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Chapter"
        assert data["chapter_number"] == 1

    async def test_get_chapter_by_id(self, client: AsyncClient) -> None:
        """Test getting a chapter by ID."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Chapter for Get",
            "status": "draft"
        }
        create_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/chapters/{chapter_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chapter_id
        assert data["title"] == "Chapter for Get"

    async def test_update_chapter(self, client: AsyncClient) -> None:
        """Test updating a chapter."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Chapter to Update",
            "status": "draft"
        }
        create_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = create_response.json()["id"]

        update_data = {"title": "Updated Chapter"}
        response = await client.patch(f"/api/v1/chapters/{chapter_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Chapter"

    async def test_delete_chapter(self, client: AsyncClient) -> None:
        """Test deleting a chapter."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Chapter to Delete",
            "status": "draft"
        }
        create_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/chapters/{chapter_id}")

        assert response.status_code in (200, 204)


class TestScenesAPI:
    """Tests for Scenes API endpoints."""

    async def test_list_scenes_empty(self, client: AsyncClient) -> None:
        """Test listing scenes when none exist."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Test Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        response = await client.get(f"/api/v1/scenes/chapter/{chapter_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_create_scene(self, client: AsyncClient) -> None:
        """Test creating a new scene."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Test Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        scene_data = {
            "chapter_id": chapter_id,
            "scene_order": 1,
            "location": "Test Location",
            "content": "Test scene content."
        }
        response = await client.post("/api/v1/scenes", json=scene_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["location"] == "Test Location"

    async def test_get_scene_by_id(self, client: AsyncClient) -> None:
        """Test getting a scene by ID."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Test Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        scene_data = {
            "chapter_id": chapter_id,
            "scene_order": 1,
            "location": "Scene for Get",
            "content": "Content"
        }
        create_response = await client.post("/api/v1/scenes", json=scene_data)
        scene_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/scenes/{scene_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == scene_id

    async def test_update_scene(self, client: AsyncClient) -> None:
        """Test updating a scene."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Test Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        scene_data = {
            "chapter_id": chapter_id,
            "scene_order": 1,
            "location": "Original Location",
            "content": "Content"
        }
        create_response = await client.post("/api/v1/scenes", json=scene_data)
        scene_id = create_response.json()["id"]

        update_data = {"location": "Updated Location"}
        response = await client.patch(f"/api/v1/scenes/{scene_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["location"] == "Updated Location"

    async def test_delete_scene(self, client: AsyncClient) -> None:
        """Test deleting a scene."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Test Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        scene_data = {
            "chapter_id": chapter_id,
            "scene_order": 1,
            "location": "Scene to Delete",
            "content": "Content"
        }
        create_response = await client.post("/api/v1/scenes", json=scene_data)
        scene_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/scenes/{scene_id}")

        assert response.status_code in (200, 204)


class TestWorldSettingsAPI:
    """Tests for WorldSettings API endpoints."""

    async def test_list_world_settings_empty(self, client: AsyncClient) -> None:
        """Test listing world settings when none exist."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        response = await client.get(f"/api/v1/world-settings/project/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_create_world_setting(self, client: AsyncClient) -> None:
        """Test creating a new world setting."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        setting_data = {
            "project_id": project_id,
            "name": "Test Location",
            "category": "geography",
            "content": "A test world setting."
        }
        response = await client.post("/api/v1/world-settings", json=setting_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Location"
        assert data["category"] == "geography"

    async def test_get_world_setting_by_id(self, client: AsyncClient) -> None:
        """Test getting a world setting by ID."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        setting_data = {
            "project_id": project_id,
            "name": "Setting for Get",
            "category": "geography",
            "content": "Content"
        }
        create_response = await client.post("/api/v1/world-settings", json=setting_data)
        setting_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/world-settings/{setting_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == setting_id

    async def test_update_world_setting(self, client: AsyncClient) -> None:
        """Test updating a world setting."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        setting_data = {
            "project_id": project_id,
            "name": "Setting to Update",
            "category": "geography",
            "content": "Content"
        }
        create_response = await client.post("/api/v1/world-settings", json=setting_data)
        setting_id = create_response.json()["id"]

        update_data = {"name": "Updated Setting"}
        response = await client.patch(f"/api/v1/world-settings/{setting_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Setting"

    async def test_delete_world_setting(self, client: AsyncClient) -> None:
        """Test deleting a world setting."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        setting_data = {
            "project_id": project_id,
            "name": "Setting to Delete",
            "category": "geography",
            "content": "Content"
        }
        create_response = await client.post("/api/v1/world-settings", json=setting_data)
        setting_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/world-settings/{setting_id}")

        assert response.status_code in (200, 204)


class TestCleanup:
    """Tests for cleanup operations."""

    async def test_delete_project_cascade(self, client: AsyncClient) -> None:
        """Test deleting a project cleans up related resources."""
        # Create project with related data
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Add a character
        character_data = {
            "project_id": project_id,
            "name": "Test Character",
            "role": "protagonist"
        }
        await client.post("/api/v1/characters", json=character_data)

        # Add a chapter
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Test Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        # Add a scene
        scene_data = {
            "chapter_id": chapter_id,
            "scene_order": 1,
            "location": "Test",
            "content": "Content"
        }
        await client.post("/api/v1/scenes", json=scene_data)

        # Delete project
        response = await client.delete(f"/api/v1/projects/{project_id}")

        assert response.status_code in (200, 204)

        # Verify project is gone
        get_response = await client.get(f"/api/v1/projects/{project_id}")
        assert get_response.status_code == 404
