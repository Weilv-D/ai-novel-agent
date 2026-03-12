"""Tests for suggestion schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    SuggestionCreate,
    SuggestionUpdate,
    SuggestionResponse,
    SuggestionActionRequest,
    SuggestionActionResult,
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
        """Test SuggestionUpdate schema."""
        data = {
            "status": "patched",
            "content": {"name": "Bob", "age": 30},
        }
        schema = SuggestionUpdate(**data)
        assert schema.status == "patched"
        assert schema.content == {"name": "Bob", "age": 30}
        assert schema.impact_analysis is None

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
