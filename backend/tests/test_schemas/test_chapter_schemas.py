"""Tests for chapter and scene schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    ChapterCreate,
    ChapterUpdate,
    SceneCreate,
    SceneUpdate,
    VolumeCreate,
    VolumeUpdate,
)


class TestVolumeSchemas:
    """Tests for Volume schemas."""

    def test_volume_create_valid(self):
        """Test valid VolumeCreate schema."""
        project_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "volume_number": 1,
            "title": "Book One",
            "outline": "Introduction",
        }
        schema = VolumeCreate(**data)
        assert schema.project_id == project_id
        assert schema.volume_number == 1
        assert schema.title == "Book One"

    def test_volume_create_minimal(self):
        """Test VolumeCreate with minimal required fields."""
        project_id = uuid.uuid4()
        schema = VolumeCreate(project_id=project_id)
        assert schema.project_id == project_id
        assert schema.volume_number is None
        assert schema.title is None

    def test_volume_update(self):
        """Test VolumeUpdate schema."""
        data = {"title": "Updated Title", "volume_number": 2}
        schema = VolumeUpdate(**data)
        assert schema.title == "Updated Title"
        assert schema.volume_number == 2


class TestChapterSchemas:
    """Tests for Chapter schemas."""

    def test_chapter_create_valid(self):
        """Test valid ChapterCreate schema."""
        project_id = uuid.uuid4()
        volume_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "volume_id": volume_id,
            "chapter_number": 1,
            "title": "Chapter One",
            "status": "draft",
        }
        schema = ChapterCreate(**data)
        assert schema.project_id == project_id
        assert schema.volume_id == volume_id
        assert schema.chapter_number == 1
        assert schema.status == "draft"

    def test_chapter_create_without_volume(self):
        """Test ChapterCreate without volume."""
        project_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "chapter_number": 1,
        }
        schema = ChapterCreate(**data)
        assert schema.project_id == project_id
        assert schema.volume_id is None

    def test_chapter_number_validation(self):
        """Test chapter number must be >= 1."""
        project_id = uuid.uuid4()
        with pytest.raises(ValidationError):
            ChapterCreate(project_id=project_id, chapter_number=0)

    def test_chapter_update_partial(self):
        """Test ChapterUpdate with partial data."""
        data = {"title": "New Title", "status": "writing"}
        schema = ChapterUpdate(**data)
        assert schema.title == "New Title"
        assert schema.status == "writing"
        assert schema.chapter_number is None

    def test_chapter_status_valid_values(self):
        """Test valid chapter status values."""
        project_id = uuid.uuid4()
        for status in ["draft", "writing", "completed"]:
            schema = ChapterCreate(project_id=project_id, chapter_number=1, status=status)
            assert schema.status == status

    def test_chapter_status_invalid_value(self):
        """Test invalid chapter status value raises ValidationError."""
        project_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            ChapterCreate(project_id=project_id, chapter_number=1, status="invalid_status")
        assert "status" in str(exc_info.value).lower()

    def test_chapter_update_status_invalid(self):
        """Test ChapterUpdate with invalid status value."""
        with pytest.raises(ValidationError) as exc_info:
            ChapterUpdate(status="not_a_valid_status")
        assert "status" in str(exc_info.value).lower()


class TestSceneSchemas:
    """Tests for Scene schemas."""

    def test_scene_create_valid(self):
        """Test valid SceneCreate schema."""
        chapter_id = uuid.uuid4()
        character_id = uuid.uuid4()
        data = {
            "chapter_id": chapter_id,
            "scene_order": 1,
            "pov_character_id": character_id,
            "location": "Castle",
            "content": "The story begins...",
            "meta": {"time": "morning", "weather": "rainy"},
        }
        schema = SceneCreate(**data)
        assert schema.chapter_id == chapter_id
        assert schema.scene_order == 1
        assert schema.pov_character_id == character_id
        assert schema.location == "Castle"
        assert schema.meta == {"time": "morning", "weather": "rainy"}

    def test_scene_create_minimal(self):
        """Test SceneCreate with minimal required fields."""
        chapter_id = uuid.uuid4()
        schema = SceneCreate(chapter_id=chapter_id, scene_order=1)
        assert schema.chapter_id == chapter_id
        assert schema.scene_order == 1
        assert schema.pov_character_id is None
        assert schema.meta == {}

    def test_scene_order_validation(self):
        """Test scene order must be >= 1."""
        chapter_id = uuid.uuid4()
        with pytest.raises(ValidationError):
            SceneCreate(chapter_id=chapter_id, scene_order=0)

    def test_scene_update(self):
        """Test SceneUpdate schema."""
        data = {"content": "Updated content", "location": "Forest"}
        schema = SceneUpdate(**data)
        assert schema.content == "Updated content"
        assert schema.location == "Forest"
