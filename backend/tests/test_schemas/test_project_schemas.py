"""Tests for project schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)


class TestProjectSchemas:
    """Tests for Project schemas."""

    def test_project_create_valid(self):
        """Test valid ProjectCreate schema."""
        data = {
            "name": "My Novel",
            "genre": "Fantasy",
            "target_audience": "Young Adult",
            "target_word_count": 80000,
            "status": "drafting",
        }
        schema = ProjectCreate(**data)
        assert schema.name == "My Novel"
        assert schema.genre == "Fantasy"
        assert schema.status == "drafting"
        assert schema.target_word_count == 80000

    def test_project_create_minimal(self):
        """Test ProjectCreate with minimal required fields."""
        data = {"name": "My Novel"}
        schema = ProjectCreate(**data)
        assert schema.name == "My Novel"
        assert schema.status == ProjectStatus.DRAFTING
        assert schema.genre is None

    def test_project_create_default_status(self):
        """Test ProjectCreate with default status."""
        schema = ProjectCreate(name="Test Project")
        assert schema.status == "drafting"

    def test_project_name_validation(self):
        """Test project name min_length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(name="")
        assert "name" in str(exc_info.value).lower()

    def test_project_target_word_count_validation(self):
        """Test target_word_count must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(name="Test", target_word_count=-1)
        assert "target_word_count" in str(exc_info.value).lower()

    def test_project_update_partial(self):
        """Test ProjectUpdate with partial data."""
        data = {
            "name": "Updated Novel",
            "status": "writing",
            "target_word_count": 100000,
        }
        schema = ProjectUpdate(**data)
        assert schema.name == "Updated Novel"
        assert schema.status == "writing"
        assert schema.target_word_count == 100000
        assert schema.genre is None

    def test_project_status_valid_values(self):
        """Test valid project status values."""
        for status in ["drafting", "writing", "revising", "completed"]:
            schema = ProjectCreate(name="Test", status=status)
            assert schema.status == status

    def test_project_status_invalid_value(self):
        """Test invalid project status value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate(name="Test", status="invalid_status")
        assert "status" in str(exc_info.value).lower()

    def test_project_update_status_invalid(self):
        """Test ProjectUpdate with invalid status value."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectUpdate(status="not_a_valid_status")
        assert "status" in str(exc_info.value).lower()

    def test_project_status_constants(self):
        """Test ProjectStatus constant class."""
        assert ProjectStatus.DRAFTING == "drafting"
        assert ProjectStatus.WRITING == "writing"
        assert ProjectStatus.REVISING == "revising"
        assert ProjectStatus.COMPLETED == "completed"

    def test_project_response(self):
        """Test ProjectResponse schema."""
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()
        from datetime import datetime

        data = {
            "id": project_id,
            "user_id": user_id,
            "name": "Test Novel",
            "genre": "Sci-Fi",
            "target_audience": "Adult",
            "target_word_count": 100000,
            "status": "writing",
            "summary": "A test novel",
            "notes": "Some notes",
            "metadata": {"key": "value"},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        schema = ProjectResponse(**data)
        assert schema.id == project_id
        assert schema.user_id == user_id
        assert schema.status == "writing"
