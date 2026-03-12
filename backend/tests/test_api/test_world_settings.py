"""Tests for WorldSetting API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.world_setting import WorldSettingResponse


class TestListWorldSettingsByProject:
    """Tests for GET /api/v1/world-settings/project/{project_id}."""

    def test_list_world_settings_empty(self):
        """Test listing world settings when none exist."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch(
            "app.api.v1.world_settings.world_setting_service.get_by_project",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/world-settings/project/{project_id}")

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []

    def test_list_world_settings_with_data(self):
        """Test listing world settings with existing data."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = WorldSettingResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            category="magic_system",
            name="Mana Circulation",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.world_settings.world_setting_service.get_by_project",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/world-settings/project/{project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Mana Circulation"


class TestListWorldSettingsByCategory:
    """Tests for GET /api/v1/world-settings/project/{project_id}/category/{category}."""

    def test_list_by_category(self):
        """Test listing world settings filtered by category."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        category = "magic_system"

        mock_response = WorldSettingResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            category=category,
            name="Mana Circulation",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.world_settings.world_setting_service.get_by_category",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(
                f"/api/v1/world-settings/project/{project_id}/category/{category}"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["category"] == category


class TestCreateWorldSetting:
    """Tests for POST /api/v1/world-settings."""

    def test_create_world_setting_valid(self):
        """Test creating a world setting with valid data."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        setting_data = {
            "project_id": str(project_id),
            "category": "magic_system",
            "name": "Mana Circulation",
        }

        mock_response = WorldSettingResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            category="magic_system",
            name="Mana Circulation",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.world_settings.world_setting_service.create_with_project",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/world-settings", json=setting_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["name"] == "Mana Circulation"


class TestGetWorldSetting:
    """Tests for GET /api/v1/world-settings/{id}."""

    def test_get_world_setting_found(self):
        """Test getting an existing world setting."""
        client = TestClient(app)
        setting_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = WorldSettingResponse(
            id=setting_id,
            project_id=project_id,
            category="geography",
            name="The Capital",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.world_settings.world_setting_service.get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/world-settings/{setting_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(setting_id)


class TestUpdateWorldSetting:
    """Tests for PATCH /api/v1/world-settings/{id}."""

    def test_update_world_setting_valid(self):
        """Test updating a world setting with valid data."""
        client = TestClient(app)
        setting_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = WorldSettingResponse(
            id=setting_id,
            project_id=project_id,
            category="geography",
            name="Updated Name",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.world_settings.world_setting_service.get", new_callable=AsyncMock
        ) as mock_get:
            with patch(
                "app.api.v1.world_settings.world_setting_service.update",
                new_callable=AsyncMock,
            ) as mock_update:
                mock_get.return_value = mock_response
                mock_update.return_value = mock_response

                response = client.patch(
                    f"/api/v1/world-settings/{setting_id}", json={"name": "Updated Name"}
                )

                assert response.status_code == status.HTTP_200_OK


class TestDeleteWorldSetting:
    """Tests for DELETE /api/v1/world-settings/{id}."""

    def test_delete_world_setting_success(self):
        """Test deleting a world setting successfully."""
        client = TestClient(app)
        setting_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = WorldSettingResponse(
            id=setting_id,
            project_id=project_id,
            category="geography",
            name="The Capital",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.world_settings.world_setting_service.delete", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/v1/world-settings/{setting_id}")

            assert response.status_code == status.HTTP_200_OK
