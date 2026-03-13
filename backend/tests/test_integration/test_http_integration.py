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


class TestVolumesAPI:
    """Tests for Volumes API endpoints."""

    async def test_list_volumes_empty(self, client: AsyncClient) -> None:
        """Test listing volumes when none exist."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        response = await client.get(f"/api/v1/volumes/project/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_create_volume(self, client: AsyncClient) -> None:
        """Test creating a new volume."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        volume_data = {
            "project_id": project_id,
            "volume_number": 1,
            "title": "Test Volume"
        }
        response = await client.post("/api/v1/volumes", json=volume_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Volume"
        assert data["volume_number"] == 1

    async def test_get_volume_by_id(self, client: AsyncClient) -> None:
        """Test getting a volume by ID."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        volume_data = {
            "project_id": project_id,
            "volume_number": 1,
            "title": "Volume for Get"
        }
        create_response = await client.post("/api/v1/volumes", json=volume_data)
        volume_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/volumes/{volume_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == volume_id
        assert data["title"] == "Volume for Get"

    async def test_update_volume(self, client: AsyncClient) -> None:
        """Test updating a volume."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        volume_data = {
            "project_id": project_id,
            "volume_number": 1,
            "title": "Volume to Update"
        }
        create_response = await client.post("/api/v1/volumes", json=volume_data)
        volume_id = create_response.json()["id"]

        update_data = {"title": "Updated Volume"}
        response = await client.patch(f"/api/v1/volumes/{volume_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Volume"

    async def test_delete_volume(self, client: AsyncClient) -> None:
        """Test deleting a volume."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        volume_data = {
            "project_id": project_id,
            "volume_number": 1,
            "title": "Volume to Delete"
        }
        create_response = await client.post("/api/v1/volumes", json=volume_data)
        volume_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/volumes/{volume_id}")

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

    async def test_create_chapter_with_volume(self, client: AsyncClient) -> None:
        """Test creating a chapter with volume_id association."""
        # Create project and volume
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        volume_data = {
            "project_id": project_id,
            "volume_number": 1,
            "title": "Test Volume"
        }
        volume_response = await client.post("/api/v1/volumes", json=volume_data)
        volume_id = volume_response.json()["id"]

        # Create chapter with volume_id
        chapter_data = {
            "project_id": project_id,
            "volume_id": volume_id,
            "chapter_number": 1,
            "title": "Chapter in Volume",
            "status": "draft"
        }
        response = await client.post("/api/v1/chapters", json=chapter_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert data["volume_id"] == volume_id
        assert data["title"] == "Chapter in Volume"

    async def test_list_chapters_by_volume(self, client: AsyncClient) -> None:
        """Test listing chapters by volume_id."""
        # Create project and volume
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        volume_data = {
            "project_id": project_id,
            "volume_number": 1,
            "title": "Test Volume"
        }
        volume_response = await client.post("/api/v1/volumes", json=volume_data)
        volume_id = volume_response.json()["id"]

        # Create chapters with and without volume
        chapter_with_volume = {
            "project_id": project_id,
            "volume_id": volume_id,
            "chapter_number": 1,
            "title": "Chapter in Volume",
            "status": "draft"
        }
        await client.post("/api/v1/chapters", json=chapter_with_volume)

        chapter_without_volume = {
            "project_id": project_id,
            "chapter_number": 2,
            "title": "Standalone Chapter",
            "status": "draft"
        }
        await client.post("/api/v1/chapters", json=chapter_without_volume)

        # List chapters by volume
        response = await client.get(f"/api/v1/chapters/volume/{volume_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["volume_id"] == volume_id
        assert data[0]["title"] == "Chapter in Volume"


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


class TestSuggestionsAPI:
    """Tests for Suggestions API endpoints."""

    async def test_list_suggestions_empty(self, client: AsyncClient) -> None:
        """Test listing suggestions when none exist."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        response = await client.get(f"/api/v1/suggestions?project_id={project_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_create_suggestion(self, client: AsyncClient) -> None:
        """Test creating a new suggestion."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # First create a chapter as target
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Target Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        suggestion_data = {
            "project_id": project_id,
            "target_type": "chapter",
            "target_id": chapter_id,
            "type": "content_gen",
            "content": {"suggestion": "Add more dialogue"}
        }
        response = await client.post("/api/v1/suggestions", json=suggestion_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["target_type"] == "chapter"
        assert data["status"] == "draft"

    async def test_suggestion_confirm_action(self, client: AsyncClient) -> None:
        """Test confirming a suggestion."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create chapter and suggestion
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Target Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        suggestion_data = {
            "project_id": project_id,
            "target_type": "chapter",
            "target_id": chapter_id,
            "type": "content_gen",
            "content": {"suggestion": "Test suggestion"}
        }
        create_response = await client.post("/api/v1/suggestions", json=suggestion_data)
        suggestion_id = create_response.json()["id"]

        action_data = {"action": "confirm"}
        response = await client.post(f"/api/v1/suggestions/{suggestion_id}/action", json=action_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "confirm"

    async def test_suggestion_discard_action(self, client: AsyncClient) -> None:
        """Test discarding a suggestion."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create chapter and suggestion
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Target Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        suggestion_data = {
            "project_id": project_id,
            "target_type": "chapter",
            "target_id": chapter_id,
            "type": "content_gen",
            "content": {"suggestion": "Test suggestion to discard"}
        }
        create_response = await client.post("/api/v1/suggestions", json=suggestion_data)
        suggestion_id = create_response.json()["id"]

        action_data = {"action": "discard"}
        response = await client.post(f"/api/v1/suggestions/{suggestion_id}/action", json=action_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "discard"

    async def test_list_suggestions_by_target(self, client: AsyncClient) -> None:
        """Test listing suggestions filtered by target object."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create two chapters as targets
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Target Chapter 1",
            "status": "draft"
        }
        chapter1_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter1_id = chapter1_response.json()["id"]

        chapter_data["chapter_number"] = 2
        chapter_data["title"] = "Target Chapter 2"
        chapter2_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter2_id = chapter2_response.json()["id"]

        # Create suggestions for different targets
        suggestion_data = {
            "project_id": project_id,
            "target_type": "chapter",
            "target_id": chapter1_id,
            "type": "content_gen",
            "content": {"suggestion": "Fix Chapter 1"}
        }
        await client.post("/api/v1/suggestions", json=suggestion_data)

        suggestion_data["target_id"] = chapter2_id
        suggestion_data["content"] = {"suggestion": "Fix Chapter 2"}
        await client.post("/api/v1/suggestions", json=suggestion_data)

        # Query suggestions by target
        response = await client.get(
            f"/api/v1/suggestions/target/chapter/{chapter1_id}?project_id={project_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["target_id"] == chapter1_id

    async def test_count_pending_suggestions(self, client: AsyncClient) -> None:
        """Test counting pending (draft/patched) suggestions."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create a chapter as target
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Target Chapter",
            "status": "draft"
        }
        chapter_response = await client.post("/api/v1/chapters", json=chapter_data)
        chapter_id = chapter_response.json()["id"]

        # Create suggestions with different statuses
        suggestion_data = {
            "project_id": project_id,
            "target_type": "chapter",
            "target_id": chapter_id,
            "type": "content_gen",
            "content": {"suggestion": "Draft suggestion"}
        }
        await client.post("/api/v1/suggestions", json=suggestion_data)

        suggestion_data["content"] = {"suggestion": "Another draft"}
        await client.post("/api/v1/suggestions", json=suggestion_data)

        # Count pending suggestions
        response = await client.get(f"/api/v1/suggestions/pending/count?project_id={project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2


class TestDependenciesAPI:
    """Tests for Dependencies API endpoints."""

    async def test_query_dependencies_empty(self, client: AsyncClient) -> None:
        """Test querying dependencies when none exist."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        response = await client.get(f"/api/v1/dependencies?project_id={project_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_create_dependency(self, client: AsyncClient) -> None:
        """Test creating a new dependency."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create chapters as source and target
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Source Chapter",
            "status": "draft"
        }
        source_response = await client.post("/api/v1/chapters", json=chapter_data)
        source_id = source_response.json()["id"]

        chapter_data["chapter_number"] = 2
        chapter_data["title"] = "Target Chapter"
        target_response = await client.post("/api/v1/chapters", json=chapter_data)
        target_id = target_response.json()["id"]

        dependency_data = {
            "project_id": project_id,
            "source_type": "chapter",
            "source_id": source_id,
            "target_type": "chapter",
            "target_id": target_id,
            "dependency_type": "precedes"
        }
        response = await client.post("/api/v1/dependencies", json=dependency_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["dependency_type"] == "precedes"

    async def test_get_dependency_by_id(self, client: AsyncClient) -> None:
        """Test getting a dependency by ID."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create chapters
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Source Chapter",
            "status": "draft"
        }
        source_response = await client.post("/api/v1/chapters", json=chapter_data)
        source_id = source_response.json()["id"]

        chapter_data["chapter_number"] = 2
        chapter_data["title"] = "Target Chapter"
        target_response = await client.post("/api/v1/chapters", json=chapter_data)
        target_id = target_response.json()["id"]

        dependency_data = {
            "project_id": project_id,
            "source_type": "chapter",
            "source_id": source_id,
            "target_type": "chapter",
            "target_id": target_id,
            "dependency_type": "precedes"
        }
        create_response = await client.post("/api/v1/dependencies", json=dependency_data)
        dependency_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/dependencies/{dependency_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == dependency_id

    async def test_delete_dependency(self, client: AsyncClient) -> None:
        """Test deleting a dependency."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create chapters
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Source Chapter",
            "status": "draft"
        }
        source_response = await client.post("/api/v1/chapters", json=chapter_data)
        source_id = source_response.json()["id"]

        chapter_data["chapter_number"] = 2
        chapter_data["title"] = "Target Chapter"
        target_response = await client.post("/api/v1/chapters", json=chapter_data)
        target_id = target_response.json()["id"]

        dependency_data = {
            "project_id": project_id,
            "source_type": "chapter",
            "source_id": source_id,
            "target_type": "chapter",
            "target_id": target_id,
            "dependency_type": "precedes"
        }
        create_response = await client.post("/api/v1/dependencies", json=dependency_data)
        dependency_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/dependencies/{dependency_id}")

        assert response.status_code in (200, 204)

    async def test_analyze_impact(self, client: AsyncClient) -> None:
        """Test analyzing impact of modifying a source object."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create chapters as source and target
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Source Chapter",
            "status": "draft"
        }
        source_response = await client.post("/api/v1/chapters", json=chapter_data)
        source_id = source_response.json()["id"]

        chapter_data["chapter_number"] = 2
        chapter_data["title"] = "Target Chapter 1"
        target1_response = await client.post("/api/v1/chapters", json=chapter_data)
        target1_id = target1_response.json()["id"]

        chapter_data["chapter_number"] = 3
        chapter_data["title"] = "Target Chapter 2"
        target2_response = await client.post("/api/v1/chapters", json=chapter_data)
        target2_id = target2_response.json()["id"]

        # Create dependencies
        dependency_data = {
            "project_id": project_id,
            "source_type": "chapter",
            "source_id": source_id,
            "target_type": "chapter",
            "target_id": target1_id,
            "dependency_type": "precedes"
        }
        await client.post("/api/v1/dependencies", json=dependency_data)

        dependency_data["target_id"] = target2_id
        await client.post("/api/v1/dependencies", json=dependency_data)

        # Analyze impact
        analyze_request = {
            "source_type": "chapter",
            "source_id": source_id
        }
        response = await client.post(
            f"/api/v1/dependencies/analyze?project_id={project_id}",
            json=analyze_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "chapter"
        assert data["source_id"] == str(source_id)
        assert len(data["impacted_objects"]) == 2
        assert data["total_count"] == 2

    async def test_analyze_reverse_impact(self, client: AsyncClient) -> None:
        """Test reverse impact analysis - what depends on a target."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create chapters
        chapter_data = {
            "project_id": project_id,
            "chapter_number": 1,
            "title": "Source 1",
            "status": "draft"
        }
        source1_response = await client.post("/api/v1/chapters", json=chapter_data)
        source1_id = source1_response.json()["id"]

        chapter_data["chapter_number"] = 2
        chapter_data["title"] = "Source 2"
        source2_response = await client.post("/api/v1/chapters", json=chapter_data)
        source2_id = source2_response.json()["id"]

        chapter_data["chapter_number"] = 3
        chapter_data["title"] = "Target Chapter"
        target_response = await client.post("/api/v1/chapters", json=chapter_data)
        target_id = target_response.json()["id"]

        # Create dependencies pointing to the same target
        dependency_data = {
            "project_id": project_id,
            "source_type": "chapter",
            "source_id": source1_id,
            "target_type": "chapter",
            "target_id": target_id,
            "dependency_type": "precedes"
        }
        await client.post("/api/v1/dependencies", json=dependency_data)

        dependency_data["source_id"] = source2_id
        await client.post("/api/v1/dependencies", json=dependency_data)

        # Analyze reverse impact
        response = await client.post(
            f"/api/v1/dependencies/analyze/reverse/chapter/{target_id}?project_id={project_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "chapter"
        assert data["source_id"] == str(target_id)
        assert len(data["impacted_objects"]) == 2
        assert data["total_count"] == 2


class TestSnapshotsAPI:
    """Tests for Snapshots API endpoints."""

    async def test_list_snapshots_empty(self, client: AsyncClient) -> None:
        """Test listing snapshots when none exist."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        response = await client.get(f"/api/v1/snapshots?project_id={project_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_create_snapshot(self, client: AsyncClient) -> None:
        """Test creating a new snapshot."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        snapshot_data = {
            "project_id": project_id,
            "target_type": "project",
            "target_id": project_id,
            "data": {"name": "Test Project State"}
        }
        response = await client.post("/api/v1/snapshots", json=snapshot_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["target_type"] == "project"

    async def test_get_snapshot_by_id(self, client: AsyncClient) -> None:
        """Test getting a snapshot by ID."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        snapshot_data = {
            "project_id": project_id,
            "target_type": "project",
            "target_id": project_id,
            "data": {"name": "Test State"}
        }
        create_response = await client.post("/api/v1/snapshots", json=snapshot_data)
        snapshot_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/snapshots/{snapshot_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == snapshot_id

    async def test_delete_snapshot(self, client: AsyncClient) -> None:
        """Test deleting a snapshot."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        snapshot_data = {
            "project_id": project_id,
            "target_type": "project",
            "target_id": project_id,
            "data": {"name": "Test State"}
        }
        create_response = await client.post("/api/v1/snapshots", json=snapshot_data)
        snapshot_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/snapshots/{snapshot_id}")

        assert response.status_code in (200, 204)

    async def test_get_latest_snapshot_by_target(self, client: AsyncClient) -> None:
        """Test getting the latest snapshot for a specific target."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create a snapshot
        snapshot_data = {
            "project_id": project_id,
            "target_type": "project",
            "target_id": project_id,
            "data": {"label": "test snapshot", "version": 1}
        }
        create_response = await client.post("/api/v1/snapshots", json=snapshot_data)
        snapshot_id = create_response.json()["id"]

        # Get latest snapshot for the target
        response = await client.get(
            f"/api/v1/snapshots/target/project/{project_id}/latest?project_id={project_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == snapshot_id
        assert data["target_type"] == "project"
        assert data["target_id"] == str(project_id)
        assert data["data"]["label"] == "test snapshot"

    async def test_rollback_to_snapshot(self, client: AsyncClient) -> None:
        """Test rollback endpoint that prepares snapshot data for restoration."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create a snapshot
        snapshot_data = {
            "project_id": project_id,
            "target_type": "chapter",
            "target_id": project_id,
            "data": {"title": "Old Chapter Title", "content": "Old content"}
        }
        create_response = await client.post("/api/v1/snapshots", json=snapshot_data)
        snapshot_id = create_response.json()["id"]

        # Request rollback data
        rollback_request = {"snapshot_id": snapshot_id}
        response = await client.post(
            f"/api/v1/snapshots/rollback?project_id={project_id}",
            json=rollback_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == snapshot_id
        assert "rolled_back_at" in data
        assert "message" in data


class TestMemoriesAPI:
    """Tests for Memories API endpoints."""

    async def test_list_memories_empty(self, client: AsyncClient) -> None:
        """Test listing memories when none exist."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        response = await client.get(f"/api/v1/memories?project_id={project_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_create_memory(self, client: AsyncClient) -> None:
        """Test creating a new memory."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        memory_data = {
            "project_id": project_id,
            "content": "The protagonist has a fear of heights",
            "memory_type": "fact",
            "auto_embed": False  # Skip embedding for HTTP test
        }
        response = await client.post("/api/v1/memories", json=memory_data)

        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["content"] == "The protagonist has a fear of heights"
        assert data["memory_type"] == "fact"

    async def test_get_memory_by_id(self, client: AsyncClient) -> None:
        """Test getting a memory by ID."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        memory_data = {
            "project_id": project_id,
            "content": "Test memory fact",
            "memory_type": "fact",
            "auto_embed": False
        }
        create_response = await client.post("/api/v1/memories", json=memory_data)
        memory_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/memories/{memory_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == memory_id
        assert data["content"] == "Test memory fact"

    async def test_delete_memory(self, client: AsyncClient) -> None:
        """Test deleting a memory."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        memory_data = {
            "project_id": project_id,
            "content": "Memory to delete",
            "memory_type": "fact",
            "auto_embed": False
        }
        create_response = await client.post("/api/v1/memories", json=memory_data)
        memory_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/memories/{memory_id}")

        assert response.status_code in (200, 204)

    async def test_search_memories_by_type(self, client: AsyncClient) -> None:
        """Test listing memories filtered by type."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create memories of different types
        memory_data = {
            "project_id": project_id,
            "content": "Character fact",
            "memory_type": "character_fact",
            "auto_embed": False
        }
        await client.post("/api/v1/memories", json=memory_data)

        memory_data["content"] = "Plot fact"
        memory_data["memory_type"] = "plot_fact"
        await client.post("/api/v1/memories", json=memory_data)

        memory_data["content"] = "World fact"
        memory_data["memory_type"] = "world_fact"
        await client.post("/api/v1/memories", json=memory_data)

        # Query memories by type
        response = await client.get(f"/api/v1/memories/type/character_fact?project_id={project_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["memory_type"] == "character_fact"

    async def test_count_memories(self, client: AsyncClient) -> None:
        """Test counting memories with optional type filter."""
        project_response = await client.post("/api/v1/projects", json={"name": "Test", "genre": "fiction"})
        project_id = project_response.json()["id"]

        # Create memories
        memory_data = {
            "project_id": project_id,
            "content": "Fact 1",
            "memory_type": "fact",
            "auto_embed": False
        }
        await client.post("/api/v1/memories", json=memory_data)

        memory_data["content"] = "Fact 2"
        await client.post("/api/v1/memories", json=memory_data)

        memory_data["content"] = "Plot point"
        memory_data["memory_type"] = "plot"
        await client.post("/api/v1/memories", json=memory_data)

        # Count all memories
        response = await client.get(f"/api/v1/memories/count?project_id={project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3

        # Count by type
        response = await client.get(f"/api/v1/memories/count?project_id={project_id}&memory_type=fact")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2


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
