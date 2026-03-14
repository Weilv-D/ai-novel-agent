"""Tests for Project API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.core.personal import PERSONAL_USER_ID
from app.main import app
from app.schemas.project import ProjectResponse


class TestListProjects:
    """Tests for GET /api/v1/projects."""

    def test_list_projects_empty(self):
        """Test listing projects when none exist."""
        client = TestClient(app)

        with patch("app.api.v1.projects.project_service.get_by_user", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = client.get("/api/v1/projects")

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []
            assert mock_get.await_args.kwargs["user_id"] == PERSONAL_USER_ID

    def test_list_projects_with_data(self):
        """Test listing projects with existing data."""
        client = TestClient(app)

        # Use actual ProjectResponse for mock
        mock_response = ProjectResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Novel",
            genre="Fantasy",
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.projects.project_service.get_by_user", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get("/api/v1/projects")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Test Novel"
            assert mock_get.await_args.kwargs["user_id"] == PERSONAL_USER_ID


class TestCreateProject:
    """Tests for POST /api/v1/projects."""

    def test_create_project_valid(self):
        """Test creating a project with valid data."""
        client = TestClient(app)

        project_data = {
            "name": "My Novel",
            "genre": "Fantasy",
            "target_audience": "Young Adult",
            "target_word_count": 80000,
        }

        mock_response = ProjectResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="My Novel",
            genre="Fantasy",
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.projects.project_service.create_with_user", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/projects", json=project_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["name"] == "My Novel"
            assert mock_create.await_args.kwargs["user_id"] == PERSONAL_USER_ID

    def test_create_project_invalid_schema(self):
        """Test creating a project with invalid schema."""
        client = TestClient(app)

        # Missing required field 'name'
        project_data = {
            "genre": "Fantasy",
        }

        response = client.post("/api/v1/projects", json=project_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_list_projects_requires_api_key_when_configured(self):
        """Test project endpoints require API key when ADMIN_API_KEY is configured."""
        client = TestClient(app)

        with patch("app.api.deps.get_settings") as mock_settings:
            mock_settings.return_value.admin_api_key = "secret-key"
            mock_settings.return_value.api_key_header = "X-API-Key"

            response = client.get("/api/v1/projects")

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_projects_accepts_valid_api_key(self):
        """Test configured API key grants access to project endpoints."""
        client = TestClient(app)

        with patch("app.api.deps.get_settings") as mock_settings:
            mock_settings.return_value.admin_api_key = "secret-key"
            mock_settings.return_value.api_key_header = "X-API-Key"

            with patch("app.api.v1.projects.project_service.get_by_user", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = []

                response = client.get("/api/v1/projects", headers={"X-API-Key": "secret-key"})

                assert response.status_code == status.HTTP_200_OK


class TestGetProject:
    """Tests for GET /api/v1/projects/{id}."""

    def test_get_project_found(self):
        """Test getting an existing project."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = ProjectResponse(
            id=project_id,
            user_id=uuid.uuid4(),
            name="Test Novel",
            genre="Fantasy",
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.projects.project_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/projects/{project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(project_id)
            assert data["name"] == "Test Novel"

    def test_get_project_not_found(self):
        """Test getting a non-existent project."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        from app.core.exceptions import NotFoundException

        with patch("app.api.v1.projects.project_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = NotFoundException("Project not found")

            response = client.get(f"/api/v1/projects/{project_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateProject:
    """Tests for PATCH /api/v1/projects/{id}."""

    def test_update_project_valid(self):
        """Test updating a project with valid data."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = ProjectResponse(
            id=project_id,
            user_id=uuid.uuid4(),
            name="Updated Name",
            genre="Fantasy",
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.projects.project_service.get", new_callable=AsyncMock) as mock_get:
            with patch(
                "app.api.v1.projects.project_service.update", new_callable=AsyncMock
            ) as mock_update:
                mock_get.return_value = mock_response
                mock_update.return_value = mock_response

                response = client.patch(
                    f"/api/v1/projects/{project_id}", json={"name": "Updated Name"}
                )

                assert response.status_code == status.HTTP_200_OK


class TestDeleteProject:
    """Tests for DELETE /api/v1/projects/{id}."""

    def test_delete_project_success(self):
        """Test deleting a project successfully."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = ProjectResponse(
            id=project_id,
            user_id=uuid.uuid4(),
            name="Test Novel",
            genre="Fantasy",
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.projects.project_service.delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/v1/projects/{project_id}")

            assert response.status_code == status.HTTP_200_OK
