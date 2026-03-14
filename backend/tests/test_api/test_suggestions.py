"""Tests for Suggestion API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.suggestion import SuggestionStatus
from app.schemas.suggestion import SuggestionResponse


class TestListSuggestions:
    """Tests for GET /api/v1/suggestions."""

    def test_list_suggestions_empty(self):
        """Test listing suggestions when none exist."""
        client = TestClient(app)

        with patch("app.api.v1.suggestions.suggestion_service.get_by_project", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/suggestions?project_id={uuid.uuid4()}")

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []

    def test_list_suggestions_with_data(self):
        """Test listing suggestions with existing data."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        mock_response = SuggestionResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            target_type="character",
            target_id=uuid.uuid4(),
            type="character_edit",
            content={"name": "New Name"},
            status=SuggestionStatus.DRAFT,
            impact_analysis=None,
            committed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.suggestions.suggestion_service.get_by_project", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/suggestions?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["target_type"] == "character"

    def test_list_suggestions_with_status_filter(self):
        """Test listing suggestions with status filter."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch("app.api.v1.suggestions.suggestion_service.get_by_project", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/suggestions?project_id={project_id}&status=draft")

            assert response.status_code == status.HTTP_200_OK
            mock_get.assert_called_once()

    def test_list_suggestions_missing_project_id(self):
        """Test listing suggestions without project_id raises error."""
        client = TestClient(app)

        response = client.get("/api/v1/suggestions")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCreateSuggestion:
    """Tests for POST /api/v1/suggestions."""

    def test_create_suggestion_valid(self):
        """Test creating a suggestion with valid data."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        suggestion_data = {
            "project_id": str(project_id),
            "target_type": "character",
            "target_id": str(target_id),
            "type": "character_edit",
            "content": {"name": "New Name", "reason": "Development"},
        }

        mock_response = SuggestionResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            target_type="character",
            target_id=target_id,
            type="character_edit",
            content={"name": "New Name", "reason": "Development"},
            status=SuggestionStatus.DRAFT,
            impact_analysis=None,
            committed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.suggestions.suggestion_service.create_with_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/suggestions", json=suggestion_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["target_type"] == "character"
            assert data["status"] == "draft"

    def test_create_suggestion_invalid_schema(self):
        """Test creating a suggestion with invalid schema."""
        client = TestClient(app)

        # Missing required fields
        suggestion_data = {"target_type": "character"}

        response = client.post("/api/v1/suggestions", json=suggestion_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetSuggestion:
    """Tests for GET /api/v1/suggestions/{id}."""

    def test_get_suggestion_found(self):
        """Test getting an existing suggestion."""
        client = TestClient(app)
        suggestion_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = SuggestionResponse(
            id=suggestion_id,
            project_id=project_id,
            target_type="chapter",
            target_id=uuid.uuid4(),
            type="chapter_edit",
            content={"summary": "New summary"},
            status=SuggestionStatus.DRAFT,
            impact_analysis=None,
            committed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.suggestions.suggestion_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/suggestions/{suggestion_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(suggestion_id)
            assert data["target_type"] == "chapter"

    def test_get_suggestion_not_found(self):
        """Test getting a non-existent suggestion."""
        client = TestClient(app)
        suggestion_id = uuid.uuid4()

        from app.core.exceptions import NotFoundException

        with patch("app.api.v1.suggestions.suggestion_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = NotFoundException("Suggestion not found")

            response = client.get(f"/api/v1/suggestions/{suggestion_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateSuggestion:
    """Tests for PATCH /api/v1/suggestions/{id}."""

    def test_update_suggestion_valid(self):
        """Test updating a suggestion with valid data."""
        client = TestClient(app)
        suggestion_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = SuggestionResponse(
            id=suggestion_id,
            project_id=project_id,
            target_type="character",
            target_id=uuid.uuid4(),
            type="character_edit",
            content={"name": "Updated"},
            status=SuggestionStatus.DRAFT,
            impact_analysis=None,
            committed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.suggestions.suggestion_service.get", new_callable=AsyncMock) as mock_get:
            with patch("app.api.v1.suggestions.suggestion_service.update", new_callable=AsyncMock) as mock_update:
                mock_get.return_value = mock_response
                mock_update.return_value = mock_response

                response = client.patch(
                    f"/api/v1/suggestions/{suggestion_id}", json={"content": {"name": "Updated"}}
                )

                assert response.status_code == status.HTTP_200_OK


class TestSuggestionAction:
    """Tests for POST /api/v1/suggestions/{id}/action."""

    def test_action_confirm(self):
        """Test confirming a suggestion."""
        client = TestClient(app)
        suggestion_id = uuid.uuid4()

        with patch("app.api.v1.suggestions.suggestion_service.confirm", new_callable=AsyncMock) as mock_confirm:
            mock_confirm.return_value = None

            response = client.post(
                f"/api/v1/suggestions/{suggestion_id}/action",
                json={"action": "confirm", "impact_analysis": {"affected": ["obj1"]}},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["action"] == "confirm"
            assert "confirmed" in data["message"].lower()

    def test_action_discard(self):
        """Test discarding a suggestion."""
        client = TestClient(app)
        suggestion_id = uuid.uuid4()

        with patch("app.api.v1.suggestions.suggestion_service.discard", new_callable=AsyncMock) as mock_discard:
            mock_discard.return_value = None

            response = client.post(f"/api/v1/suggestions/{suggestion_id}/action", json={"action": "discard"})

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["action"] == "discard"
            assert "discarded" in data["message"].lower()

    def test_action_commit(self):
        """Test committing a suggestion."""
        client = TestClient(app)
        suggestion_id = uuid.uuid4()

        with patch("app.api.v1.suggestions.suggestion_service.commit", new_callable=AsyncMock) as mock_commit:
            mock_commit.return_value = None

            response = client.post(f"/api/v1/suggestions/{suggestion_id}/action", json={"action": "commit"})

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["action"] == "commit"
            assert "committed" in data["message"].lower()

    def test_action_invalid(self):
        """Test action with invalid action type."""
        client = TestClient(app)
        suggestion_id = uuid.uuid4()

        # Pydantic should reject invalid action values
        response = client.post(f"/api/v1/suggestions/{suggestion_id}/action", json={"action": "invalid"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteSuggestion:
    """Tests for DELETE /api/v1/suggestions/{id}."""

    def test_delete_suggestion_success(self):
        """Test deleting a suggestion successfully."""
        client = TestClient(app)
        suggestion_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_response = SuggestionResponse(
            id=suggestion_id,
            project_id=project_id,
            target_type="character",
            target_id=uuid.uuid4(),
            type="character_edit",
            content={"name": "To Delete"},
            status=SuggestionStatus.DRAFT,
            impact_analysis=None,
            committed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.suggestions.suggestion_service.delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/v1/suggestions/{suggestion_id}")

            assert response.status_code == status.HTTP_200_OK


class TestListTargetSuggestions:
    """Tests for GET /api/v1/suggestions/target/{target_type}/{target_id}."""

    def test_list_target_suggestions(self):
        """Test listing suggestions for a specific target."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        with patch(
            "app.api.v1.suggestions.suggestion_service.get_by_target", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/suggestions/target/character/{target_id}?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            mock_get.assert_called_once()


class TestCountPendingSuggestions:
    """Tests for GET /api/v1/suggestions/pending/count."""

    def test_count_pending_suggestions(self):
        """Test counting pending suggestions."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch(
            "app.api.v1.suggestions.suggestion_service.get_pending_count", new_callable=AsyncMock
        ) as mock_count:
            mock_count.return_value = 5

            response = client.get(f"/api/v1/suggestions/pending/count?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["count"] == 5
