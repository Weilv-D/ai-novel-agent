"""Integration tests for Character service layer with real DB."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.character import CharacterCreate, CharacterUpdate
from app.schemas.project import ProjectCreate
from app.services.character import character_service
from app.services.project import project_service


class TestCharacterServiceGetByProject:
    """Tests for character_service.get_by_project with real database."""

    @pytest.mark.asyncio
    async def test_get_by_project_empty(self, db_session: AsyncSession):
        """Test get_by_project returns empty list when no characters exist."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        result = await character_service.get_by_project(db_session, project_id=project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_project_with_characters(self, db_session: AsyncSession):
        """Test get_by_project returns characters for specific project."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        other_project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Other Project", genre="Sci-Fi"),
        )

        # Create characters for different projects
        char1 = await character_service.create_with_project(
            db_session,
            obj_in=CharacterCreate(name="Character 1", role="protagonist", project_id=project.id),
            project_id=project.id,
        )
        char2 = await character_service.create_with_project(
            db_session,
            obj_in=CharacterCreate(name="Character 2", role="antagonist", project_id=project.id),
            project_id=project.id,
        )
        await character_service.create_with_project(
            db_session,
            obj_in=CharacterCreate(name="Other Character", role="supporting", project_id=other_project.id),
            project_id=other_project.id,
        )

        # Get characters for project
        result = await character_service.get_by_project(db_session, project_id=project.id)
        assert len(result) == 2
        char_ids = {c.id for c in result}
        assert char1.id in char_ids
        assert char2.id in char_ids

    @pytest.mark.asyncio
    async def test_get_by_project_with_pagination(self, db_session: AsyncSession):
        """Test get_by_project with skip and limit parameters."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        # Create 5 characters
        for i in range(5):
            await character_service.create_with_project(
                db_session,
                obj_in=CharacterCreate(name=f"Character {i}", role="supporting", project_id=project.id),
                project_id=project.id,
            )

        # Test pagination
        result = await character_service.get_by_project(db_session, project_id=project.id, skip=0, limit=2)
        assert len(result) == 2

        result = await character_service.get_by_project(db_session, project_id=project.id, skip=2, limit=2)
        assert len(result) == 2

        result = await character_service.get_by_project(db_session, project_id=project.id, skip=4, limit=10)
        assert len(result) == 1


class TestCharacterServiceCreateWithProject:
    """Tests for character_service.create_with_project with real database."""

    @pytest.mark.asyncio
    async def test_create_with_project_valid(self, db_session: AsyncSession):
        """Test creating a character with valid data."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        char_in = CharacterCreate(
            name="Hero",
            role="protagonist",
            project_id=project.id,
        )

        result = await character_service.create_with_project(
            db_session,
            obj_in=char_in,
            project_id=project.id,
        )

        assert result.id is not None
        assert result.name == "Hero"
        assert result.role == "protagonist"
        assert result.project_id == project.id

    @pytest.mark.asyncio
    async def test_create_with_project_minimal(self, db_session: AsyncSession):
        """Test creating a character with minimal required fields."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        char_in = CharacterCreate(name="Side Character", project_id=project.id)

        result = await character_service.create_with_project(
            db_session,
            obj_in=char_in,
            project_id=project.id,
        )

        assert result.id is not None
        assert result.name == "Side Character"
        assert result.project_id == project.id


class TestCharacterServiceUpdate:
    """Tests for character_service.update with real database."""

    @pytest.mark.asyncio
    async def test_update_partial(self, db_session: AsyncSession):
        """Test updating specific fields of a character."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        character = await character_service.create_with_project(
            db_session,
            obj_in=CharacterCreate(name="Original Name", role="supporting", project_id=project.id),
            project_id=project.id,
        )

        updated = await character_service.update(
            db_session,
            db_obj=character,
            obj_in=CharacterUpdate(name="Updated Name"),
        )

        assert updated.id == character.id
        assert updated.name == "Updated Name"
        assert updated.role == "supporting"  # Unchanged
