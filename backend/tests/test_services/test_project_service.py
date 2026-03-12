"""Integration tests for Project service layer with real DB."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project import project_service


class TestProjectServiceGetByUser:
    """Tests for project_service.get_by_user with real database."""

    @pytest.mark.asyncio
    async def test_get_by_user_empty(self, db_session: AsyncSession):
        """Test get_by_user returns empty list when no projects exist."""
        user_id = uuid4()
        result = await project_service.get_by_user(db_session, user_id=user_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_user_with_projects(self, db_session: AsyncSession):
        """Test get_by_user returns projects for specific user."""
        user_id = uuid4()
        other_user_id = uuid4()

        # Create projects for different users
        project1 = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Project 1", genre="Fantasy"),
            user_id=user_id,
        )
        project2 = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Project 2", genre="Sci-Fi"),
            user_id=user_id,
        )
        await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Other Project", genre="Mystery"),
            user_id=other_user_id,
        )

        # Get projects for user_id
        result = await project_service.get_by_user(db_session, user_id=user_id)
        assert len(result) == 2
        project_ids = {p.id for p in result}
        assert project1.id in project_ids
        assert project2.id in project_ids

    @pytest.mark.asyncio
    async def test_get_by_user_with_pagination(self, db_session: AsyncSession):
        """Test get_by_user with skip and limit parameters."""
        user_id = uuid4()

        # Create 5 projects
        for i in range(5):
            await project_service.create_with_user(
                db_session,
                obj_in=ProjectCreate(name=f"Project {i}", genre="Fantasy"),
                user_id=user_id,
            )

        # Test pagination
        result = await project_service.get_by_user(db_session, user_id=user_id, skip=0, limit=2)
        assert len(result) == 2

        result = await project_service.get_by_user(db_session, user_id=user_id, skip=2, limit=2)
        assert len(result) == 2

        result = await project_service.get_by_user(db_session, user_id=user_id, skip=4, limit=10)
        assert len(result) == 1


class TestProjectServiceCreateWithUser:
    """Tests for project_service.create_with_user with real database."""

    @pytest.mark.asyncio
    async def test_create_with_user_valid(self, db_session: AsyncSession):
        """Test creating a project with valid data."""
        user_id = uuid4()
        project_in = ProjectCreate(
            name="Test Novel",
            genre="Fantasy",
            target_audience="Young Adult",
            target_word_count=80000,
        )

        result = await project_service.create_with_user(db_session, obj_in=project_in, user_id=user_id)

        assert result.id is not None
        assert isinstance(result.id, UUID)
        assert result.name == "Test Novel"
        assert result.genre == "Fantasy"
        assert result.target_audience == "Young Adult"
        assert result.target_word_count == 80000
        assert result.user_id == user_id
        assert result.status == "drafting"  # Default value

    @pytest.mark.asyncio
    async def test_create_with_user_minimal(self, db_session: AsyncSession):
        """Test creating a project with minimal required fields."""
        user_id = uuid4()
        project_in = ProjectCreate(name="Minimal Project")

        result = await project_service.create_with_user(db_session, obj_in=project_in, user_id=user_id)

        assert result.id is not None
        assert result.name == "Minimal Project"
        assert result.user_id == user_id


class TestProjectServiceGet:
    """Tests for project_service.get with real database."""

    @pytest.mark.asyncio
    async def test_get_existing(self, db_session: AsyncSession):
        """Test getting an existing project by ID."""
        user_id = uuid4()
        created = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
            user_id=user_id,
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
        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Original Name", genre="Fantasy"),
            user_id=user_id,
        )

        updated = await project_service.update(
            db_session,
            db_obj=project,
            obj_in=ProjectUpdate(name="Updated Name"),
        )

        assert updated.id == project.id
        assert updated.name == "Updated Name"
        assert updated.genre == "Fantasy"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_with_dict(self, db_session: AsyncSession):
        """Test updating a project with a dictionary."""
        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="Original", genre="Fantasy"),
            user_id=user_id,
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
        user_id = uuid4()
        project = await project_service.create_with_user(
            db_session,
            obj_in=ProjectCreate(name="To Delete", genre="Fantasy"),
            user_id=user_id,
        )
        project_id = project.id

        deleted = await project_service.delete(db_session, id=project_id)

        assert deleted.id == project_id
        assert deleted.name == "To Delete"

        # Verify project is actually deleted
        from app.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException, match="Project not found"):
            await project_service.get(db_session, id=project_id)
