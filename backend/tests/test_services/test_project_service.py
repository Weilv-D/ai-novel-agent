"""Integration tests for Project service layer with real DB."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project import project_service


class TestProjectServiceListProjects:
    """Tests for project_service.list_projects with real database."""

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, db_session: AsyncSession):
        """Test list_projects returns empty list when no projects exist."""
        result = await project_service.list_projects(db_session)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_projects_with_projects(self, db_session: AsyncSession):
        """Test list_projects returns stored projects."""
        project1 = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Project 1", genre="Fantasy"),
        )
        project2 = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Project 2", genre="Sci-Fi"),
        )
        project3 = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Project 3", genre="Mystery"),
        )

        result = await project_service.list_projects(db_session)
        assert len(result) == 3
        project_ids = {p.id for p in result}
        assert project1.id in project_ids
        assert project2.id in project_ids
        assert project3.id in project_ids

    @pytest.mark.asyncio
    async def test_list_projects_with_pagination(self, db_session: AsyncSession):
        """Test list_projects with skip and limit parameters."""
        for i in range(5):
            await project_service.create_project(
                db_session,
                obj_in=ProjectCreate(name=f"Project {i}", genre="Fantasy"),
            )

        result = await project_service.list_projects(db_session, skip=0, limit=2)
        assert len(result) == 2

        result = await project_service.list_projects(db_session, skip=2, limit=2)
        assert len(result) == 2

        result = await project_service.list_projects(db_session, skip=4, limit=10)
        assert len(result) == 1


class TestProjectServiceCreateProject:
    """Tests for project_service.create_project with real database."""

    @pytest.mark.asyncio
    async def test_create_project_valid(self, db_session: AsyncSession):
        """Test creating a project with valid data."""
        project_in = ProjectCreate(
            name="Test Novel",
            genre="Fantasy",
            target_audience="Young Adult",
            target_word_count=80000,
        )

        result = await project_service.create_project(db_session, obj_in=project_in)

        assert result.id is not None
        assert isinstance(result.id, UUID)
        assert result.name == "Test Novel"
        assert result.genre == "Fantasy"
        assert result.target_audience == "Young Adult"
        assert result.target_word_count == 80000
        assert result.status == "drafting"

    @pytest.mark.asyncio
    async def test_create_project_minimal(self, db_session: AsyncSession):
        """Test creating a project with minimal required fields."""
        project_in = ProjectCreate(name="Minimal Project")

        result = await project_service.create_project(db_session, obj_in=project_in)

        assert result.id is not None
        assert result.name == "Minimal Project"

    @pytest.mark.asyncio
    async def test_create_project_derives_story_outline_from_summary_and_notes(self, db_session: AsyncSession):
        """Legacy summary/notes should seed the project story outline."""
        result = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(
                name="Outline Seed",
                summary="这是项目简介",
                notes="这是项目备注",
            ),
        )

        assert result.story_outline is not None
        assert "这是项目简介" in result.story_outline
        assert "这是项目备注" in result.story_outline

    @pytest.mark.asyncio
    async def test_create_project_preserves_explicit_story_outline(self, db_session: AsyncSession):
        """Explicit story outline should win over legacy fallback fields."""
        result = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(
                name="Explicit Outline",
                summary="旧简介",
                notes="旧备注",
                story_outline="明确的项目大纲",
            ),
        )

        assert result.story_outline == "明确的项目大纲"


class TestProjectServiceGet:
    """Tests for project_service.get with real database."""

    @pytest.mark.asyncio
    async def test_get_existing(self, db_session: AsyncSession):
        """Test getting an existing project by ID."""
        created = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        result = await project_service.get(db_session, id=created.id)

        assert result.id == created.id
        assert result.name == "Test Project"

    @pytest.mark.asyncio
    async def test_get_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent project raises NotFoundException."""
        from app.core.exceptions import NotFoundException

        non_existent_id = uuid4()

        with pytest.raises(NotFoundException, match="Project not found"):
            await project_service.get(db_session, id=non_existent_id)


class TestProjectServiceUpdate:
    """Tests for project_service.update with real database."""

    @pytest.mark.asyncio
    async def test_update_partial(self, db_session: AsyncSession):
        """Test updating specific fields of a project."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Original Name", genre="Fantasy"),
        )

        updated = await project_service.update(
            db_session,
            db_obj=project,
            obj_in=ProjectUpdate(name="Updated Name"),
        )

        assert updated.id == project.id
        assert updated.name == "Updated Name"
        assert updated.genre == "Fantasy"

    @pytest.mark.asyncio
    async def test_update_with_dict(self, db_session: AsyncSession):
        """Test updating a project with a dictionary."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Original", genre="Fantasy"),
        )

        updated = await project_service.update(
            db_session,
            db_obj=project,
            obj_in={"name": "Updated", "genre": "Sci-Fi"},
        )

        assert updated.name == "Updated"
        assert updated.genre == "Sci-Fi"


class TestProjectServiceDelete:
    """Tests for project_service.delete with real database."""

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session: AsyncSession):
        """Test deleting a project successfully."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="To Delete", genre="Fantasy"),
        )
        project_id = project.id

        deleted = await project_service.delete(db_session, id=project_id)

        assert deleted.id == project_id
        assert deleted.name == "To Delete"

        from app.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException, match="Project not found"):
            await project_service.get(db_session, id=project_id)
