"""Tests for Snapshot API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.snapshot import RollbackResponse, SnapshotResponse


class TestListSnapshots:
    """Tests for GET /api/v1/snapshots."""

    def test_list_snapshots_empty(self):
        """Test listing snapshots when none exist."""
        client = TestClient(app)

        with patch("app.api.v1.snapshots.snapshot_service.get_by_project", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/snapshots?project_id={uuid.uuid4()}")

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []

    def test_list_snapshots_with_data(self):
        """Test listing snapshots with existing data."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = SnapshotResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            target_type="character",
            target_id=target_id,
            data={"name": "Hero"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.snapshots.snapshot_service.get_by_project", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/snapshots?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["target_type"] == "character"

    def test_list_snapshots_missing_project_id(self):
        """Test listing snapshots without project_id raises error."""
        client = TestClient(app)

        response = client.get("/api/v1/snapshots")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListTargetSnapshots:
    """Tests for GET /api/v1/snapshots/target/{target_type}/{target_id}."""

    def test_list_target_snapshots(self):
        """Test listing snapshots for a specific target."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        with patch(
            "app.api.v1.snapshots.snapshot_service.get_by_target", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/snapshots/target/character/{target_id}?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            mock_get.assert_called_once()


class TestGetLatestSnapshot:
    """Tests for GET /api/v1/snapshots/target/{target_type}/{target_id}/latest."""

    def test_get_latest_snapshot_found(self):
        """Test getting the latest snapshot for a target."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = SnapshotResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            target_type="character",
            target_id=target_id,
            data={"name": "Hero v2"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.snapshots.snapshot_service.get_latest_by_target", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/snapshots/target/character/{target_id}/latest?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["data"]["name"] == "Hero v2"

    def test_get_latest_snapshot_not_found(self):
        """Test getting latest snapshot when none exist."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        with patch(
            "app.api.v1.snapshots.snapshot_service.get_latest_by_target", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            response = client.get(f"/api/v1/snapshots/target/character/{target_id}/latest?project_id={project_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateSnapshot:
    """Tests for POST /api/v1/snapshots."""

    def test_create_snapshot_valid(self):
        """Test creating a snapshot with valid data."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        snapshot_data = {
            "project_id": str(project_id),
            "target_type": "character",
            "target_id": str(target_id),
            "data": {"name": "Hero", "level": 5},
        }

        mock_response = SnapshotResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            target_type="character",
            target_id=target_id,
            data={"name": "Hero", "level": 5},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.snapshots.snapshot_service.create_with_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/snapshots", json=snapshot_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["target_type"] == "character"
            assert data["data"]["name"] == "Hero"

    def test_create_snapshot_invalid_schema(self):
        """Test creating a snapshot with invalid schema."""
        client = TestClient(app)

        # Missing required fields
        snapshot_data = {"target_type": "character"}

        response = client.post("/api/v1/snapshots", json=snapshot_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetSnapshot:
    """Tests for GET /api/v1/snapshots/{id}."""

    def test_get_snapshot_found(self):
        """Test getting an existing snapshot."""
        client = TestClient(app)
        snapshot_id = uuid.uuid4()
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = SnapshotResponse(
            id=snapshot_id,
            project_id=project_id,
            target_type="character",
            target_id=target_id,
            data={"name": "Hero"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.snapshots.snapshot_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/snapshots/{snapshot_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(snapshot_id)
            assert data["target_type"] == "character"

    def test_get_snapshot_not_found(self):
        """Test getting a non-existent snapshot."""
        client = TestClient(app)
        snapshot_id = uuid.uuid4()

        from app.core.exceptions import NotFoundException

        with patch("app.api.v1.snapshots.snapshot_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = NotFoundException("Snapshot not found")

            response = client.get(f"/api/v1/snapshots/{snapshot_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetSnapshotData:
    """Tests for GET /api/v1/snapshots/{id}/data."""

    def test_get_snapshot_data(self):
        """Test getting snapshot data for rollback."""
        client = TestClient(app)
        snapshot_id = uuid.uuid4()

        mock_data = {"name": "Hero", "level": 10, "class": "Warrior"}

        with patch(
            "app.api.v1.snapshots.snapshot_service.get_snapshot_data", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_data

            response = client.get(f"/api/v1/snapshots/{snapshot_id}/data")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == "Hero"
            assert data["level"] == 10

    def test_get_snapshot_data_not_found(self):
        """Test getting data for non-existent snapshot."""
        client = TestClient(app)
        snapshot_id = uuid.uuid4()

        with patch(
            "app.api.v1.snapshots.snapshot_service.get_snapshot_data", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            response = client.get(f"/api/v1/snapshots/{snapshot_id}/data")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateSnapshot:
    """Tests for PATCH /api/v1/snapshots/{id}."""

    def test_update_snapshot_valid(self):
        """Test updating a snapshot with valid data."""
        client = TestClient(app)
        snapshot_id = uuid.uuid4()
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = SnapshotResponse(
            id=snapshot_id,
            project_id=project_id,
            target_type="character",
            target_id=target_id,
            data={"name": "Hero", "level": 15},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.snapshots.snapshot_service.get", new_callable=AsyncMock) as mock_get:
            with patch("app.api.v1.snapshots.snapshot_service.update", new_callable=AsyncMock) as mock_update:
                mock_get.return_value = mock_response
                mock_update.return_value = mock_response

                response = client.patch(
                    f"/api/v1/snapshots/{snapshot_id}",
                    json={"data": {"name": "Hero", "level": 15}},
                )

                assert response.status_code == status.HTTP_200_OK


class TestDeleteSnapshot:
    """Tests for DELETE /api/v1/snapshots/{id}."""

    def test_delete_snapshot_success(self):
        """Test deleting a snapshot successfully."""
        client = TestClient(app)
        snapshot_id = uuid.uuid4()
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = SnapshotResponse(
            id=snapshot_id,
            project_id=project_id,
            target_type="character",
            target_id=target_id,
            data={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.snapshots.snapshot_service.delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/v1/snapshots/{snapshot_id}")

            assert response.status_code == status.HTTP_200_OK


class TestRollbackToSnapshot:
    """Tests for POST /api/v1/snapshots/rollback."""

    def test_rollback_to_snapshot(self):
        """Test rollback preparation for a snapshot."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        snapshot_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_snapshot = SnapshotResponse(
            id=snapshot_id,
            project_id=project_id,
            target_type="character",
            target_id=target_id,
            data={"name": "Hero v1"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.snapshots.snapshot_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_snapshot

            response = client.post(
                f"/api/v1/snapshots/rollback?project_id={project_id}",
                json={"snapshot_id": str(snapshot_id)},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["snapshot_id"] == str(snapshot_id)
            assert data["target_type"] == "character"
            assert "message" in data

    def test_rollback_wrong_project(self):
        """Test rollback with snapshot from different project."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        other_project_id = uuid.uuid4()
        snapshot_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_snapshot = SnapshotResponse(
            id=snapshot_id,
            project_id=other_project_id,
            target_type="character",
            target_id=target_id,
            data={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.snapshots.snapshot_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_snapshot

            response = client.post(
                f"/api/v1/snapshots/rollback?project_id={project_id}",
                json={"snapshot_id": str(snapshot_id)},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestCountSnapshots:
    """Tests for GET /api/v1/snapshots/count."""

    def test_count_snapshots(self):
        """Test counting snapshots for a project."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch("app.api.v1.snapshots.snapshot_service.count_by_project", new_callable=AsyncMock) as mock_count:
            mock_count.return_value = 5

            response = client.get(f"/api/v1/snapshots/count?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["count"] == 5
            assert data["project_id"] == str(project_id)

    def test_count_snapshots_with_type_filter(self):
        """Test counting snapshots with target_type filter."""
        client = TestClient(app)
        project_id = uuid.uuid4()

        with patch("app.api.v1.snapshots.snapshot_service.count_by_project", new_callable=AsyncMock) as mock_count:
            mock_count.return_value = 3

            response = client.get(f"/api/v1/snapshots/count?project_id={project_id}&target_type=character")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["count"] == 3
            assert data["target_type"] == "character"
