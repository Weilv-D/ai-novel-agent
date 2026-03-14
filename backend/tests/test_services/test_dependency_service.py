"""Integration tests for Dependency service layer with real DB."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.dependency import DependencyType
from app.models.project import Project
from app.schemas.dependency import DependencyCreate, DependencyUpdate
from app.services.dependency import dependency_service
from app.services.project import project_service


@pytest.fixture
async def test_project(db_session: AsyncSession) -> Project:
    """Create a test project for dependency tests."""
    from app.schemas.project import ProjectCreate

    user_id = uuid4()
    return await project_service.create_with_user(
        db_session,
        obj_in=ProjectCreate(name="Test Novel", genre="Fantasy"),
        user_id=user_id,
    )


class TestDependencyServiceCreate:
    """Tests for dependency_service.create_with_project."""

    @pytest.mark.asyncio
    async def test_create_dependency_valid(self, db_session: AsyncSession, test_project: Project):
        """Test creating a dependency with valid data."""
        source_id = uuid4()
        target_id = uuid4()
        dependency_in = DependencyCreate(
            project_id=test_project.id,
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type=DependencyType.REFERENCES,
        )

        result = await dependency_service.create_with_project(
            db_session, obj_in=dependency_in, project_id=test_project.id
        )

        assert result.id is not None
        assert isinstance(result.id, UUID)
        assert result.project_id == test_project.id
        assert result.source_type == "chapter"
        assert result.target_type == "character"
        assert result.dependency_type == DependencyType.REFERENCES

    @pytest.mark.asyncio
    async def test_create_dependency_minimal(self, db_session: AsyncSession, test_project: Project):
        """Test creating a dependency with minimal required fields (no dependency_type)."""
        source_id = uuid4()
        target_id = uuid4()
        dependency_in = DependencyCreate(
            project_id=test_project.id,
            source_type="volume",
            source_id=source_id,
            target_type="chapter",
            target_id=target_id,
        )

        result = await dependency_service.create_with_project(
            db_session, obj_in=dependency_in, project_id=test_project.id
        )

        assert result.id is not None
        assert result.dependency_type is None


class TestDependencyServiceGetByProject:
    """Tests for dependency_service.get_by_project."""

    @pytest.mark.asyncio
    async def test_get_by_project_empty(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_project returns empty list when no dependencies exist."""
        result = await dependency_service.get_by_project(db_session, project_id=test_project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_project_with_dependencies(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_project returns dependencies for specific project."""
        source_id = uuid4()
        target_id = uuid4()

        # Create dependencies
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="volume",
                source_id=uuid4(),
                target_type="chapter",
                target_id=source_id,
                dependency_type=DependencyType.CONTAINS,
            ),
            project_id=test_project.id,
        )

        result = await dependency_service.get_by_project(db_session, project_id=test_project.id)
        assert len(result) == 2


class TestDependencyServiceGetBySource:
    """Tests for dependency_service.get_by_source."""

    @pytest.mark.asyncio
    async def test_get_by_source(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_source returns dependencies for specific source."""
        source_id = uuid4()
        target_id1 = uuid4()
        target_id2 = uuid4()

        # Create dependencies from same source
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id1,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id2,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        # Create dependency from different source
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=uuid4(),
                target_type="character",
                target_id=target_id1,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        result = await dependency_service.get_by_source(
            db_session, project_id=test_project.id, source_type="chapter", source_id=source_id
        )
        assert len(result) == 2


class TestDependencyServiceGetByTarget:
    """Tests for dependency_service.get_by_target."""

    @pytest.mark.asyncio
    async def test_get_by_target(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_target returns dependencies pointing to specific target."""
        target_id = uuid4()
        source_id1 = uuid4()
        source_id2 = uuid4()

        # Create dependencies pointing to same target
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id1,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id2,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        result = await dependency_service.get_by_target(
            db_session, project_id=test_project.id, target_type="character", target_id=target_id
        )
        assert len(result) == 2


class TestDependencyServiceQuery:
    """Tests for dependency_service.query_dependencies."""

    @pytest.mark.asyncio
    async def test_query_by_source_type(self, db_session: AsyncSession, test_project: Project):
        """Test querying dependencies by source_type."""
        source_id = uuid4()
        target_id = uuid4()

        # Create dependencies with different source types
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="volume",
                source_id=uuid4(),
                target_type="chapter",
                target_id=source_id,
                dependency_type=DependencyType.CONTAINS,
            ),
            project_id=test_project.id,
        )

        result = await dependency_service.query_dependencies(
            db_session, project_id=test_project.id, source_type="chapter"
        )
        assert len(result) == 1
        assert result[0].source_type == "chapter"

    @pytest.mark.asyncio
    async def test_query_by_dependency_type(self, db_session: AsyncSession, test_project: Project):
        """Test querying dependencies by dependency_type."""
        source_id = uuid4()
        target_id = uuid4()

        # Create dependencies with different types
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="world_setting",
                source_id=uuid4(),
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.INFLUENCES,
            ),
            project_id=test_project.id,
        )

        result = await dependency_service.query_dependencies(
            db_session, project_id=test_project.id, dependency_type=DependencyType.REFERENCES
        )
        assert len(result) == 1
        assert result[0].dependency_type == DependencyType.REFERENCES


class TestDependencyServiceGetOrCreate:
    """Tests for dependency_service.get_or_create."""

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, db_session: AsyncSession, test_project: Project):
        """Test get_or_create creates new dependency."""
        source_id = uuid4()
        target_id = uuid4()

        result, created = await dependency_service.get_or_create(
            db_session,
            project_id=test_project.id,
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type=DependencyType.REFERENCES,
        )

        assert created is True
        assert result.source_type == "chapter"
        assert result.dependency_type == DependencyType.REFERENCES

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, db_session: AsyncSession, test_project: Project):
        """Test get_or_create returns existing dependency."""
        source_id = uuid4()
        target_id = uuid4()

        # Create initial dependency
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        # Try to create again - should return existing
        result, created = await dependency_service.get_or_create(
            db_session,
            project_id=test_project.id,
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type=DependencyType.REFERENCES,
        )

        assert created is False
        assert result.source_type == "chapter"


class TestDependencyServiceDelete:
    """Tests for dependency_service delete operations."""

    @pytest.mark.asyncio
    async def test_delete_by_target(self, db_session: AsyncSession, test_project: Project):
        """Test delete_by_target removes all dependencies pointing to target."""
        target_id = uuid4()

        # Create dependencies pointing to same target
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=uuid4(),
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=uuid4(),
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        # Create dependency pointing to different target
        other_target_id = uuid4()
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=uuid4(),
                target_type="character",
                target_id=other_target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        count = await dependency_service.delete_by_target(
            db_session, project_id=test_project.id, target_type="character", target_id=target_id
        )
        assert count == 2

        # Verify only the other dependency remains
        remaining = await dependency_service.get_by_target(
            db_session, project_id=test_project.id, target_type="character", target_id=other_target_id
        )
        assert len(remaining) == 1

    @pytest.mark.asyncio
    async def test_delete_by_source(self, db_session: AsyncSession, test_project: Project):
        """Test delete_by_source removes all dependencies from source."""
        source_id = uuid4()

        # Create dependencies from same source
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=uuid4(),
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=uuid4(),
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        count = await dependency_service.delete_by_source(
            db_session, project_id=test_project.id, source_type="chapter", source_id=source_id
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session: AsyncSession, test_project: Project):
        """Test deleting a dependency successfully."""
        source_id = uuid4()
        target_id = uuid4()
        dependency = await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        dependency_id = dependency.id

        deleted = await dependency_service.delete(db_session, id=dependency_id)

        assert deleted.id == dependency_id

        # Verify dependency is actually deleted
        with pytest.raises(NotFoundException, match="Dependency not found"):
            await dependency_service.get(db_session, id=dependency_id)


class TestDependencyServiceAnalyzeImpact:
    """Tests for dependency_service impact analysis."""

    @pytest.mark.asyncio
    async def test_analyze_impact(self, db_session: AsyncSession, test_project: Project):
        """Test analyze_impact returns affected objects."""
        source_id = uuid4()
        target_id1 = uuid4()
        target_id2 = uuid4()

        # Create dependencies from source
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="character",
                source_id=source_id,
                target_type="chapter",
                target_id=target_id1,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="character",
                source_id=source_id,
                target_type="chapter",
                target_id=target_id2,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        impacts = await dependency_service.analyze_impact(
            db_session, project_id=test_project.id, source_type="character", source_id=source_id
        )

        assert len(impacts) == 2
        impact_ids = {impact.target_id for impact in impacts}
        assert target_id1 in impact_ids
        assert target_id2 in impact_ids
        assert all(impact.target_type == "chapter" for impact in impacts)
        assert all(impact.dependency_type == DependencyType.REFERENCES for impact in impacts)

    @pytest.mark.asyncio
    async def test_analyze_impact_empty(self, db_session: AsyncSession, test_project: Project):
        """Test analyze_impact returns empty list when no dependencies."""
        source_id = uuid4()

        impacts = await dependency_service.analyze_impact(
            db_session, project_id=test_project.id, source_type="character", source_id=source_id
        )

        assert len(impacts) == 0

    @pytest.mark.asyncio
    async def test_analyze_reverse_impact(self, db_session: AsyncSession, test_project: Project):
        """Test analyze_reverse_impact returns dependent sources."""
        target_id = uuid4()
        source_id1 = uuid4()
        source_id2 = uuid4()

        # Create dependencies pointing to target
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id1,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )
        await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id2,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        impacts = await dependency_service.analyze_reverse_impact(
            db_session, project_id=test_project.id, target_type="character", target_id=target_id
        )

        assert len(impacts) == 2
        impact_ids = {impact.target_id for impact in impacts}
        assert source_id1 in impact_ids
        assert source_id2 in impact_ids
        assert all(impact.target_type == "chapter" for impact in impacts)


class TestDependencyServiceGet:
    """Tests for dependency_service.get."""

    @pytest.mark.asyncio
    async def test_get_existing(self, db_session: AsyncSession, test_project: Project):
        """Test getting an existing dependency by ID."""
        source_id = uuid4()
        target_id = uuid4()
        dependency = await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        result = await dependency_service.get(db_session, id=dependency.id)

        assert result.id == dependency.id
        assert result.source_type == "chapter"

    @pytest.mark.asyncio
    async def test_get_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent dependency raises NotFoundException."""
        non_existent_id = uuid4()

        with pytest.raises(NotFoundException, match="Dependency not found"):
            await dependency_service.get(db_session, id=non_existent_id)


class TestDependencyServiceUpdate:
    """Tests for dependency_service.update."""

    @pytest.mark.asyncio
    async def test_update_dependency_type(self, db_session: AsyncSession, test_project: Project):
        """Test updating dependency type."""
        source_id = uuid4()
        target_id = uuid4()
        dependency = await dependency_service.create_with_project(
            db_session,
            obj_in=DependencyCreate(
                project_id=test_project.id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type=DependencyType.REFERENCES,
            ),
            project_id=test_project.id,
        )

        updated = await dependency_service.update(
            db_session,
            db_obj=dependency,
            obj_in=DependencyUpdate(dependency_type=DependencyType.INFLUENCES),
        )

        assert updated.id == dependency.id
        assert updated.dependency_type == DependencyType.INFLUENCES
