"""Tests for world_setting schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    WorldSettingCategory,
    WorldSettingCreate,
    WorldSettingResponse,
    WorldSettingUpdate,
)


class TestWorldSettingSchemas:
    """Tests for WorldSetting schemas."""

    def test_world_setting_create_valid(self):
        """Test valid WorldSettingCreate schema."""
        project_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "category": "magic_system",
            "name": "Mana Circulation",
            "content": "Magic flows through ley lines...",
        }
        schema = WorldSettingCreate(**data)
        assert schema.project_id == project_id
        assert schema.category == "magic_system"
        assert schema.name == "Mana Circulation"

    def test_world_setting_create_minimal(self):
        """Test WorldSettingCreate with minimal required fields."""
        project_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "category": "geography",
            "name": "The Capital",
        }
        schema = WorldSettingCreate(**data)
        assert schema.project_id == project_id
        assert schema.category == "geography"
        assert schema.content is None

    def test_world_setting_name_validation(self):
        """Test name min_length validation."""
        project_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            WorldSettingCreate(project_id=project_id, category="rules", name="")
        assert "name" in str(exc_info.value).lower()

    def test_world_setting_update_partial(self):
        """Test WorldSettingUpdate with partial data."""
        data = {
            "name": "Updated Setting",
            "category": "history",
            "content": "New content",
        }
        schema = WorldSettingUpdate(**data)
        assert schema.name == "Updated Setting"
        assert schema.category == "history"
        assert schema.meta is None

    def test_world_setting_category_valid_values(self):
        """Test valid category values."""
        project_id = uuid.uuid4()
        for category in [
            "magic_system",
            "geography",
            "history",
            "organization",
            "technology",
            "culture",
            "religion",
            "economy",
            "rules",
            "other",
        ]:
            schema = WorldSettingCreate(
                project_id=project_id, category=category, name="Test"
            )
            assert schema.category == category

    def test_world_setting_category_invalid_value(self):
        """Test invalid category value raises ValidationError."""
        project_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            WorldSettingCreate(
                project_id=project_id, category="invalid_category", name="Test"
            )
        assert "category" in str(exc_info.value).lower()

    def test_world_setting_update_category_invalid(self):
        """Test WorldSettingUpdate with invalid category value."""
        with pytest.raises(ValidationError) as exc_info:
            WorldSettingUpdate(category="not_a_valid_category")
        assert "category" in str(exc_info.value).lower()

    def test_world_setting_category_constants(self):
        """Test WorldSettingCategory constant class."""
        assert WorldSettingCategory.MAGIC_SYSTEM == "magic_system"
        assert WorldSettingCategory.GEOGRAPHY == "geography"
        assert WorldSettingCategory.HISTORY == "history"
        assert WorldSettingCategory.ORGANIZATION == "organization"
        assert WorldSettingCategory.TECHNOLOGY == "technology"
        assert WorldSettingCategory.CULTURE == "culture"
        assert WorldSettingCategory.RELIGION == "religion"
        assert WorldSettingCategory.ECONOMY == "economy"
        assert WorldSettingCategory.RULES == "rules"
        assert WorldSettingCategory.OTHER == "other"

    def test_world_setting_response(self):
        """Test WorldSettingResponse schema."""
        setting_id = uuid.uuid4()
        project_id = uuid.uuid4()
        from datetime import datetime

        data = {
            "id": setting_id,
            "project_id": project_id,
            "category": "technology",
            "name": "Airships",
            "content": "Floating vessels...",
            "metadata": {"era": "steampunk"},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        schema = WorldSettingResponse(**data)
        assert schema.id == setting_id
        assert schema.category == "technology"
