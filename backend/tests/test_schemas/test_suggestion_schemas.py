"""Tests for suggestion schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    SuggestionActionRequest,
    SuggestionActionResult,
    SuggestionCreate,
    SuggestionUpdate,
)


class TestSuggestionSchemas:
    """Tests for Suggestion schemas."""

    def test_suggestion_create_valid(self):
        """Test valid SuggestionCreate schema."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "target_type": "character",
            "target_id": target_id,
            "type": "character_edit",
            "content": {"name": "Alice", "age": 25},
            "status": "draft",
        }
        schema = SuggestionCreate(**data)
        assert schema.project_id == project_id
        assert schema.target_type == "character"
        assert schema.target_id == target_id
        assert schema.type == "character_edit"
        assert schema.content == {"name": "Alice", "age": 25}
        assert schema.status == "draft"

    def test_suggestion_create_default_status(self):
        """Test SuggestionCreate with default status."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        schema = SuggestionCreate(
            project_id=project_id,
            target_type="chapter",
            target_id=target_id,
            type="content_gen",
            content={"prompt": "Write a battle scene"},
        )
        assert schema.status == "draft"

    def test_suggestion_update(self):
        """Test SuggestionUpdate schema (content only, no status changes)."""
        data = {
            "content": {"name": "Bob", "age": 30},
        }
        schema = SuggestionUpdate(**data)
        assert schema.content == {"name": "Bob", "age": 30}
        # Note: status and impact_analysis cannot be updated via PATCH
        # Use the action endpoint (confirm/discard/commit) for state transitions

    def test_suggestion_action_request_confirm(self):
        """Test SuggestionActionRequest for confirm action."""
        data = {
            "action": "confirm",
        }
        schema = SuggestionActionRequest(**data)
        assert schema.action == "confirm"
        assert schema.impact_analysis is None

    def test_suggestion_action_request_with_impact(self):
        """Test SuggestionActionRequest with impact analysis."""
        data = {
            "action": "commit",
            "impact_analysis": {
                "affected_objects": ["character:abc123"],
                "conflicts": [],
                "risk_level": "low",
            },
        }
        schema = SuggestionActionRequest(**data)
        assert schema.action == "commit"
        assert schema.impact_analysis["risk_level"] == "low"

    def test_suggestion_action_result(self):
        """Test SuggestionActionResult schema."""
        suggestion_id = uuid.uuid4()
        data = {
            "success": True,
            "message": "Suggestion committed successfully",
            "suggestion_id": suggestion_id,
            "action": "commit",
        }
        schema = SuggestionActionResult(**data)
        assert schema.success is True
        assert schema.message == "Suggestion committed successfully"
        assert schema.suggestion_id == suggestion_id
        assert schema.action == "commit"

    def test_suggestion_status_valid_values(self):
        """Test valid suggestion status values."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        for status in ["draft", "patched", "committed", "discarded"]:
            schema = SuggestionCreate(
                project_id=project_id,
                target_type="character",
                target_id=target_id,
                type="character_edit",
                content={},
                status=status,
            )
            assert schema.status == status

    def test_suggestion_status_invalid_value(self):
        """Test invalid suggestion status value raises ValidationError."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            SuggestionCreate(
                project_id=project_id,
                target_type="character",
                target_id=target_id,
                type="character_edit",
                content={},
                status="invalid_status",
            )
        assert "status" in str(exc_info.value).lower()

    def test_suggestion_type_valid_values(self):
        """Test valid suggestion type values."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        valid_types = [
            "character_edit",
            "world_edit",
            "chapter_edit",
            "scene_edit",
            "content_gen",
            "outline_gen",
            "continuity_fix",
        ]
        for suggestion_type in valid_types:
            schema = SuggestionCreate(
                project_id=project_id,
                target_type="character",
                target_id=target_id,
                type=suggestion_type,
                content={},
            )
            assert schema.type == suggestion_type

    def test_suggestion_type_invalid_value(self):
        """Test invalid suggestion type value raises ValidationError."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            SuggestionCreate(
                project_id=project_id,
                target_type="character",
                target_id=target_id,
                type="invalid_type",
                content={},
            )
        assert "type" in str(exc_info.value).lower()

    def test_suggestion_target_type_valid_values(self):
        """Test valid target_type values."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        for target_type in ["character", "world_setting", "chapter", "scene"]:
            schema = SuggestionCreate(
                project_id=project_id,
                target_type=target_type,
                target_id=target_id,
                type="character_edit",
                content={},
            )
            assert schema.target_type == target_type

    def test_suggestion_target_type_invalid_value(self):
        """Test invalid target_type value raises ValidationError."""
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            SuggestionCreate(
                project_id=project_id,
                target_type="invalid_target",
                target_id=target_id,
                type="character_edit",
                content={},
            )
        assert "target_type" in str(exc_info.value).lower()

    def test_suggestion_action_valid_values(self):
        """Test valid action values."""
        for action in ["confirm", "discard", "commit"]:
            schema = SuggestionActionRequest(action=action)
            assert schema.action == action

    def test_suggestion_action_invalid_value(self):
        """Test invalid action value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SuggestionActionRequest(action="invalid_action")
        assert "action" in str(exc_info.value).lower()
