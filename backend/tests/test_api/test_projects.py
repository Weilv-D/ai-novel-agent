"""Tests for Project API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.agent import AgentRunResponse, AgentThreadCheckpointResponse, AgentThreadResponse
from app.schemas.project import (
    ProjectAgentSettings,
    ProjectResponse,
    ProjectTreeChapterResponse,
    ProjectTreeResponse,
    ProjectTreeVolumeResponse,
    ProjectWorkspaceResponse,
    ProjectWorkspaceSummaryResponse,
)


class TestListProjects:
    """Tests for GET /api/v1/projects."""

    def test_list_projects_empty(self):
        """Test listing projects when none exist."""
        client = TestClient(app)

        with patch("app.api.v1.projects.project_service.list_projects", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = client.get("/api/v1/projects")

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []

    def test_list_projects_with_data(self):
        """Test listing projects with existing data."""
        client = TestClient(app)

        # Use actual ProjectResponse for mock
        mock_response = ProjectResponse(
            id=uuid.uuid4(),
            name="Test Novel",
            genre="Fantasy",
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.projects.project_service.list_projects", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get("/api/v1/projects")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Test Novel"


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
            "story_outline": "项目总纲",
        }

        mock_response = ProjectResponse(
            id=uuid.uuid4(),
            name="My Novel",
            genre="Fantasy",
            story_outline="项目总纲",
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.projects.project_service.create_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/projects", json=project_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["name"] == "My Novel"
            assert data["story_outline"] == "项目总纲"

    def test_create_project_accepts_agent_profile_id(self):
        """Project creation should carry the selected agent profile."""
        client = TestClient(app)

        project_data = {
            "name": "My Novel",
            "genre": "Fantasy",
            "agent_profile_id": "xianxia_intrigue",
        }

        mock_response = ProjectResponse(
            id=uuid.uuid4(),
            name="My Novel",
            genre="Fantasy",
            agent_profile_id="xianxia_intrigue",
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.projects.project_service.create_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/projects", json=project_data)

            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["agent_profile_id"] == "xianxia_intrigue"
            assert mock_create.await_args.kwargs["obj_in"].agent_profile_id == "xianxia_intrigue"

    def test_create_project_accepts_agent_settings(self):
        """Project creation should accept project-level agent settings."""
        client = TestClient(app)

        project_data = {
            "name": "My Novel",
            "agent_settings": {
                "style_goal": "冷峻权谋",
                "tone_keywords": ["克制", "压迫感"],
                "continuity_mode": "strict",
            },
        }

        mock_response = ProjectResponse(
            id=uuid.uuid4(),
            name="My Novel",
            agent_settings=ProjectAgentSettings(
                style_goal="冷峻权谋",
                tone_keywords=["克制", "压迫感"],
                continuity_mode="strict",
            ),
            status="drafting",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.projects.project_service.create_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/projects", json=project_data)

            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["agent_settings"]["style_goal"] == "冷峻权谋"
            assert mock_create.await_args.kwargs["obj_in"].agent_settings.style_goal == "冷峻权谋"

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

            with patch("app.api.v1.projects.project_service.list_projects", new_callable=AsyncMock) as mock_get:
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
            name="Updated Name",
            genre="Fantasy",
            story_outline="更新后的项目大纲",
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
                    f"/api/v1/projects/{project_id}", json={"name": "Updated Name", "story_outline": "更新后的项目大纲"}
                )

                assert response.status_code == status.HTTP_200_OK
                assert response.json()["story_outline"] == "更新后的项目大纲"

    def test_update_project_agent_profile_id(self):
        """Project update should expose the selected profile id."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = ProjectResponse(
            id=project_id,
            name="Updated Name",
            genre="Fantasy",
            agent_profile_id="xianxia_intrigue",
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
                    f"/api/v1/projects/{project_id}", json={"agent_profile_id": "xianxia_intrigue"}
                )

                assert response.status_code == status.HTTP_200_OK
                assert response.json()["agent_profile_id"] == "xianxia_intrigue"

    def test_update_project_agent_settings(self):
        """Project update should expose project-level agent settings."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = ProjectResponse(
            id=project_id,
            name="Updated Name",
            genre="Fantasy",
            agent_settings=ProjectAgentSettings(
                tone_keywords=["冷静"],
                continuity_mode="standard",
            ),
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
                    f"/api/v1/projects/{project_id}",
                    json={"agent_settings": {"tone_keywords": ["冷静"], "continuity_mode": "standard"}},
                )

                assert response.status_code == status.HTTP_200_OK
                assert response.json()["agent_settings"]["continuity_mode"] == "standard"
                assert mock_update.await_args.kwargs["obj_in"].agent_settings.continuity_mode == "standard"


class TestProjectWorkspaceEndpoints:
    """Tests for aggregated tree/workspace project endpoints."""

    def test_get_project_tree(self):
        """Tree endpoint should return the nested volume/chapter structure."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = ProjectTreeResponse(
            project_id=project_id,
            volumes=[
                ProjectTreeVolumeResponse(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    volume_number=1,
                    title="第一卷",
                    chapters=[
                        ProjectTreeChapterResponse(
                            id=uuid.uuid4(),
                            project_id=project_id,
                            chapter_number=1,
                            title="开篇",
                            status="draft",
                        )
                    ],
                )
            ],
        )

        with patch("app.api.v1.projects.project_workspace_service.get_tree_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/projects/{project_id}/tree")

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["volumes"][0]["chapters"][0]["title"] == "开篇"

    def test_get_project_workspace(self):
        """Workspace endpoint should return aggregate project + thread state data."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_response = ProjectWorkspaceResponse(
            project=ProjectResponse(
                id=project_id,
                name="测试项目",
                agent_settings=ProjectAgentSettings(style_goal="冷峻", continuity_mode="strict"),
                status="drafting",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            agent_settings=ProjectAgentSettings(style_goal="冷峻", continuity_mode="strict"),
            tree=ProjectTreeResponse(project_id=project_id),
            default_thread=AgentThreadResponse(
                id=thread_id,
                project_id=project_id,
                title="Default",
                is_default=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            latest_checkpoint=AgentThreadCheckpointResponse(
                id=uuid.uuid4(),
                thread_id=thread_id,
                profile_id="default",
                thread_summary="summary",
                source_message_count=1,
                source_run_count=1,
                total_context_characters=42,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            current_run=AgentRunResponse(
                id=run_id,
                thread_id=thread_id,
                project_id=project_id,
                status="awaiting_confirmation",
                verification_status="pending",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            recent_runs=[],
            workspace_summary=ProjectWorkspaceSummaryResponse(
                volume_count=0,
                chapter_count=0,
                scene_count=0,
                character_count=0,
                world_setting_count=0,
                latest_run_status="awaiting_confirmation",
                context_source="live_context",
            ),
        )

        with patch("app.api.v1.projects.project_workspace_service.get_workspace_response", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/projects/{project_id}/workspace")

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["project"]["name"] == "测试项目"
            assert response.json()["agent_settings"]["style_goal"] == "冷峻"
            assert response.json()["workspace_summary"]["context_source"] == "live_context"


class TestDeleteProject:
    """Tests for DELETE /api/v1/projects/{id}."""

    def test_delete_project_success(self):
        """Test deleting a project successfully."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = ProjectResponse(
            id=project_id,
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
