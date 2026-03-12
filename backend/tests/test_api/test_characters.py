"""Tests for Character API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.character import CharacterResponse


class TestListCharactersByProject:
    """Tests for GET /api/v1/characters/project/{project_id}."""

    def test_list_characters_empty(self):
        """Test listing characters when none exist."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch(
            "app.api.v1.characters.character_service.get_by_project", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/characters/project/{project_id}")

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []

    def test_list_characters_with_data(self):
        """Test listing characters with existing data."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = CharacterResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            name="Hero",
            role="protagonist",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.characters.character_service.get_by_project", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/characters/project/{project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Hero"


class TestCreateCharacter:
    """Tests for POST /api/v1/characters."""

    def test_create_character_valid(self):
        """Test creating a character with valid data."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        character_data = {
            "project_id": str(project_id),
            "name": "Hero",
            "role": "protagonist",
        }

        mock_response = CharacterResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            name="Hero",
            role="protagonist",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.characters.character_service.create_with_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/characters", json=character_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["name"] == "Hero"


class TestGetCharacter:
    """Tests for GET /api/v1/characters/{id}."""

    def test_get_character_found(self):
        """Test getting an existing character."""
        client = TestClient(app)
        character_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = CharacterResponse(
            id=character_id,
            project_id=project_id,
            name="Hero",
            role="protagonist",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.characters.character_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/characters/{character_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(character_id)
            assert data["name"] == "Hero"


class TestUpdateCharacter:
    """Tests for PATCH /api/v1/characters/{id}."""

    def test_update_character_valid(self):
        """Test updating a character with valid data."""
        client = TestClient(app)
        character_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = CharacterResponse(
            id=character_id,
            project_id=project_id,
            name="Updated Name",
            role="protagonist",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.characters.character_service.get", new_callable=AsyncMock) as mock_get:
            with patch(
                "app.api.v1.characters.character_service.update", new_callable=AsyncMock
            ) as mock_update:
                mock_get.return_value = mock_response
                mock_update.return_value = mock_response

                response = client.patch(
                    f"/api/v1/characters/{character_id}", json={"name": "Updated Name"}
                )

                assert response.status_code == status.HTTP_200_OK


class TestDeleteCharacter:
    """Tests for DELETE /api/v1/characters/{id}."""

    def test_delete_character_success(self):
        """Test deleting a character successfully."""
        client = TestClient(app)
        character_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = CharacterResponse(
            id=character_id,
            project_id=project_id,
            name="Hero",
            role="protagonist",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.characters.character_service.delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/v1/characters/{character_id}")

            assert response.status_code == status.HTTP_200_OK
