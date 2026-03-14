"""Tests for snapshot schemas."""

import uuid
from datetime import UTC

import pytest
from pydantic import ValidationError

from app.schemas.snapshot import (
    RollbackRequest,
    RollbackResponse,
    SnapshotCreate,
    SnapshotQueryRequest,
    SnapshotUpdate,
)


class TestSnapshotSchemas:
    """Tests for Snapshot schemas."""

    def test_snapshot_create_valid(self):
        """Test valid SnapshotCreate schema."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "target_type": "character",
            "target_id": target_id,
            "data": {"name": "Hero", "description": "Main character"},
        }
        schema = SnapshotCreate(**data)
        assert schema.project_id == project_id
        assert schema.target_type == "character"
        assert schema.target_id == target_id
        assert schema.data == {"name": "Hero", "description": "Main character"}

    def test_snapshot_create_minimal(self):
        """Test SnapshotCreate with minimal data."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        schema = SnapshotCreate(
            project_id=project_id,
            target_type="chapter",
            target_id=target_id,
            data={},
        )
        assert schema.data == {}

    def test_snapshot_create_with_complex_data(self):
        """Test SnapshotCreate with nested JSON data."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        complex_data = {
            "name": "Scene 1",
            "characters": [
                {"id": str(uuid.uuid4()), "name": "Hero"},
                {"id": str(uuid.uuid4()), "name": "Villain"},
            ],
            "metadata": {"location": "Castle", "time": "Night"},
        }
        schema = SnapshotCreate(
            project_id=project_id,
            target_type="scene",
            target_id=target_id,
            data=complex_data,
        )
        assert schema.data == complex_data

    def test_snapshot_update(self):
        """Test SnapshotUpdate schema."""
        new_data = {"name": "Updated Hero", "description": "Updated description"}
        schema = SnapshotUpdate(data=new_data)
        assert schema.data == new_data

    def test_snapshot_update_empty(self):
        """Test SnapshotUpdate with no fields."""
        schema = SnapshotUpdate()
        assert schema.data is None

    def test_target_type_valid_values(self):
        """Test valid target_type values."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        valid_types = [
            "project",
            "character",
            "world_setting",
            "volume",
            "chapter",
            "scene",
            "suggestion",
        ]
        for target_type in valid_types:
            schema = SnapshotCreate(
                project_id=project_id,
                target_type=target_type,
                target_id=target_id,
                data={},
            )
            assert schema.target_type == target_type

    def test_target_type_invalid_value(self):
        """Test invalid target_type value raises ValidationError."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            SnapshotCreate(
                project_id=project_id,
                target_type="invalid_entity",
                target_id=target_id,
                data={},
            )
        assert "target_type" in str(exc_info.value).lower()

    def test_snapshot_query_request_empty(self):
        """Test SnapshotQueryRequest with no filters."""
        schema = SnapshotQueryRequest()
        assert schema.target_type is None
        assert schema.target_id is None

    def test_snapshot_query_request_with_filters(self):
        """Test SnapshotQueryRequest with filters."""
        target_id = uuid.uuid4()
        schema = SnapshotQueryRequest(
            target_type="chapter",
            target_id=target_id,
        )
        assert schema.target_type == "chapter"
        assert schema.target_id == target_id

    def test_rollback_request(self):
        """Test RollbackRequest schema."""
        snapshot_id = uuid.uuid4()
        schema = RollbackRequest(snapshot_id=snapshot_id)
        assert schema.snapshot_id == snapshot_id

    def test_rollback_response(self):
        """Test RollbackResponse schema."""
        snapshot_id = uuid.uuid4()
        target_id = uuid.uuid4()
        from datetime import datetime

        now = datetime.now(UTC)
        data = {
            "snapshot_id": snapshot_id,
            "target_type": "chapter",
            "target_id": target_id,
            "rolled_back_at": now,
            "message": "Rollback data prepared",
        }
        schema = RollbackResponse(**data)
        assert schema.snapshot_id == snapshot_id
        assert schema.target_type == "chapter"
        assert schema.target_id == target_id
        assert schema.rolled_back_at == now
        assert schema.message == "Rollback data prepared"
