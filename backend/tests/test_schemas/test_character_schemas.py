"""Tests for character schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
)


class TestCharacterSchemas:
    """Tests for Character schemas."""

    def test_character_create_valid(self):
        """Test valid CharacterCreate schema."""
        project_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "name": "Alice",
            "role": "protagonist",
            "profile": {"age": 25, "appearance": "tall"},
            "relationships": {"Bob": "friend"},
            "arc_state": {"stage": "beginning"},
        }
        schema = CharacterCreate(**data)
        assert schema.project_id == project_id
        assert schema.name == "Alice"
        assert schema.role == "protagonist"
        assert schema.profile["age"] == 25

    def test_character_create_minimal(self):
        """Test CharacterCreate with minimal required fields."""
        project_id = uuid.uuid4()
        schema = CharacterCreate(project_id=project_id, name="Bob")
        assert schema.project_id == project_id
        assert schema.name == "Bob"
        assert schema.role is None
        assert schema.profile == {}
        assert schema.relationships == {}
        assert schema.arc_state == {}

    def test_character_name_validation(self):
        """Test name min_length validation."""
        project_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            CharacterCreate(project_id=project_id, name="")
        assert "name" in str(exc_info.value).lower()

    def test_character_update_partial(self):
        """Test CharacterUpdate with partial data."""
        data = {
            "name": "Updated Name",
            "role": "antagonist",
            "notes": "Updated notes",
        }
        schema = CharacterUpdate(**data)
        assert schema.name == "Updated Name"
        assert schema.role == "antagonist"
        assert schema.notes == "Updated notes"
        assert schema.profile is None
        assert schema.relationships is None
        assert schema.arc_state is None

    def test_character_update_all_fields(self):
        """Test CharacterUpdate with all fields."""
        data = {
            "name": "Charlie",
            "role": "mentor",
            "profile": {"age": 50},
            "relationships": {"Alice": "student"},
            "arc_state": {"stage": "end"},
            "notes": "Wise old mentor",
        }
        schema = CharacterUpdate(**data)
        assert schema.name == "Charlie"
        assert schema.role == "mentor"
        assert schema.profile["age"] == 50
        assert schema.relationships["Alice"] == "student"
        assert schema.arc_state["stage"] == "end"
        assert schema.notes == "Wise old mentor"

    def test_character_response(self):
        """Test CharacterResponse schema."""
        character_id = uuid.uuid4()
        project_id = uuid.uuid4()
        from datetime import datetime

        data = {
            "id": character_id,
            "project_id": project_id,
            "name": "Diana",
            "role": "supporting",
            "profile": {"age": 30},
            "relationships": {},
            "arc_state": {},
            "notes": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        schema = CharacterResponse(**data)
        assert schema.id == character_id
        assert schema.project_id == project_id
        assert schema.name == "Diana"
        assert schema.role == "supporting"
