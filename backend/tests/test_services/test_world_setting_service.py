"""Integration tests for WorldSetting service layer with real DB."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world_setting import WorldSetting
from app.schemas.project import ProjectCreate
from app.schemas.world_setting import WorldSettingCreate, WorldSettingUpdate
from app.services.project import project_service
from app.services.world_setting import world_setting_service


class TestWorldSettingServiceGetByProject:
    """Tests for world_setting_service.get_by_project with real database."""

    @pytest.mark.asyncio
    async def test_get_by_project_empty(self, db_session: AsyncSession):
        """Test get_by_project returns empty list when no settings exist."""
        from app.schemas.project import ProjectCreate

        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
        )

        result = await world_setting_service.get_by_project(db_session, project_id=project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_project_with_settings(self, db_session: AsyncSession):
        """Test get_by_project returns settings for specific project."""
        from app.schemas.project import ProjectCreate

        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
        )
        other_project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Other Project", genre="Sci-Fi"),
            user_id=user_id,
        )

        # Create settings for different projects
        setting1 = await world_setting_service.create_with_project(
            db_session,
            obj_in=WorldSettingCreate(name="Magic System", category="magic_system", project_id=project.id),
            project_id=project.id,
        )
        setting2 = await world_setting_service.create_with_project(
            db_session,
            obj_in=WorldSettingCreate(name="Geography", category="geography", project_id=project.id),
            project_id=project.id,
        )
        await world_setting_service.create_with_project(
            db_session,
            obj_in=WorldSettingCreate(name="Technology", category="technology", project_id=other_project.id),
            project_id=other_project.id,
        )

        # Get settings for project
        result = await world_setting_service.get_by_project(db_session, project_id=project.id)
        assert len(result) == 2
        setting_ids = {s.id for s in result}
        assert setting1.id in setting_ids
        assert setting2.id in setting_ids

    @pytest.mark.asyncio
    async def test_get_by_project_with_pagination(self, db_session: AsyncSession):
        """Test get_by_project with skip and limit parameters."""
        from app.schemas.project import ProjectCreate

        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
        )

        # Create 5 settings
        for i in range(5):
            await world_setting_service.create_with_project(
                db_session,
                obj_in=WorldSettingCreate(name=f"Setting {i}", category="geography", project_id=project.id),
                project_id=project.id,
            )

        # Test pagination
        result = await world_setting_service.get_by_project(db_session, project_id=project.id, skip=0, limit=2)
        assert len(result) == 2

        result = await world_setting_service.get_by_project(db_session, project_id=project.id, skip=2, limit=2)
        assert len(result) == 2

        result = await world_setting_service.get_by_project(db_session, project_id=project.id, skip=4, limit=10)
        assert len(result) == 1


class TestWorldSettingServiceGetByCategory:
    """Tests for world_setting_service.get_by_category with real database."""

    @pytest.mark.asyncio
    async def test_get_by_category_empty(self, db_session: AsyncSession):
        """Test get_by_category returns empty list when no settings exist."""
        from app.schemas.project import ProjectCreate

        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
        )

        result = await world_setting_service.get_by_category(
            db_session, project_id=project.id, category="magic"
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_category_filters_correctly(self, db_session: AsyncSession):
        """Test get_by_category filters by category correctly."""
        from app.schemas.project import ProjectCreate

        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
        )

        # Create settings with different categories
        await world_setting_service.create_with_project(
            db_session,
            obj_in=WorldSettingCreate(name="Fire Magic", category="magic_system", project_id=project.id),
            project_id=project.id,
        )
        await world_setting_service.create_with_project(
            db_session,
            obj_in=WorldSettingCreate(name="Water Magic", category="magic_system", project_id=project.id),
            project_id=project.id,
        )
        await world_setting_service.create_with_project(
            db_session,
            obj_in=WorldSettingCreate(name="Castle", category="geography", project_id=project.id),
            project_id=project.id,
        )

        # Get magic_system category settings
        result = await world_setting_service.get_by_category(
            db_session, project_id=project.id, category="magic_system"
        )
        assert len(result) == 2
        assert all(s.category == "magic_system" for s in result)

        # Get geography category settings
        result = await world_setting_service.get_by_category(
            db_session, project_id=project.id, category="geography"
        )
        assert len(result) == 1
        assert result[0].name == "Castle"


class TestWorldSettingServiceCreateWithProject:
    """Tests for world_setting_service.create_with_project with real database."""

    @pytest.mark.asyncio
    async def test_create_with_project_valid(self, db_session: AsyncSession):
        """Test creating a world setting with valid data."""
        from app.schemas.project import ProjectCreate

        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
        )

        setting_in = WorldSettingCreate(
            name="Magic System",
            category="magic_system",
            content="A system of elemental magic",
            project_id=project.id,
        )

        result = await world_setting_service.create_with_project(
            db_session,
            obj_in=setting_in,
            project_id=project.id,
        )

        assert result.id is not None
        assert result.name == "Magic System"
        assert result.category == "magic_system"
        assert result.content == "A system of elemental magic"
        assert result.project_id == project.id

    @pytest.mark.asyncio
    async def test_create_with_project_minimal(self, db_session: AsyncSession):
        """Test creating a world setting with minimal required fields."""
        from app.schemas.project import ProjectCreate

        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
        )

        setting_in = WorldSettingCreate(name="Basic Setting", category="geography", project_id=project.id)

        result = await world_setting_service.create_with_project(
            db_session,
            obj_in=setting_in,
            project_id=project.id,
        )

        assert result.id is not None
        assert result.name == "Basic Setting"
        assert result.category == "geography"
        assert result.project_id == project.id


class TestWorldSettingServiceUpdate:
    """Tests for world_setting_service.update with real database."""

    @pytest.mark.asyncio
    async def test_update_partial(self, db_session: AsyncSession):
        """Test updating specific fields of a world setting."""
        from app.schemas.project import ProjectCreate

        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
        )

        setting = await world_setting_service.create_with_project(
            db_session,
            obj_in=WorldSettingCreate(name="Original Name", category="magic_system", project_id=project.id),
            project_id=project.id,
        )

        updated = await world_setting_service.update(
            db_session,
            db_obj=setting,
            obj_in=WorldSettingUpdate(name="Updated Name"),
        )

        assert updated.id == setting.id
        assert updated.name == "Updated Name"
        assert updated.category == "magic_system"  # Unchanged
