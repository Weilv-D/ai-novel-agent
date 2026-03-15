"""Integration tests for Snapshot service layer with real DB."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.project import Project
from app.schemas.snapshot import SnapshotCreate, SnapshotUpdate
from app.services.project import project_service
from app.services.snapshot import snapshot_service


@pytest.fixture
async def test_project(db_session: AsyncSession) -> Project:
    """Create a test project for snapshot tests."""
    from app.schemas.project import ProjectCreate
    return await project_service.create_project(
        db_session,
        obj_in=ProjectCreate(name="Test Novel", genre="Fantasy"),
    )


class TestSnapshotServiceCreate:
    """Tests for snapshot_service.create_with_project."""

    @pytest.mark.asyncio
    async def test_create_snapshot_valid(self, db_session: AsyncSession, test_project: Project):
        """Test creating a snapshot with valid data."""
        target_id = uuid4()
        snapshot_in = SnapshotCreate(
            project_id=test_project.id,
            target_type="character",
            target_id=target_id,
            data={"name": "Hero", "description": "Main character"},
        )

        result = await snapshot_service.create_with_project(
            db_session, obj_in=snapshot_in, project_id=test_project.id
        )

        assert result.id is not None
        assert isinstance(result.id, UUID)
        assert result.project_id == test_project.id
        assert result.target_type == "character"
        assert result.target_id == target_id
        assert result.data == {"name": "Hero", "description": "Main character"}

    @pytest.mark.asyncio
    async def test_create_snapshot_minimal(self, db_session: AsyncSession, test_project: Project):
        """Test creating a snapshot with empty data."""
        target_id = uuid4()
        snapshot_in = SnapshotCreate(
            project_id=test_project.id,
            target_type="chapter",
            target_id=target_id,
            data={},
        )

        result = await snapshot_service.create_with_project(
            db_session, obj_in=snapshot_in, project_id=test_project.id
        )

        assert result.id is not None
        assert result.data == {}

    @pytest.mark.asyncio
    async def test_create_snapshot_complex_data(self, db_session: AsyncSession, test_project: Project):
        """Test creating a snapshot with nested JSON data."""
        target_id = uuid4()
        complex_data = {
            "name": "Scene 1",
            "characters": [
                {"id": str(uuid4()), "name": "Hero"},
                {"id": str(uuid4()), "name": "Villain"},
            ],
            "metadata": {"location": "Castle", "time": "Night"},
        }
        snapshot_in = SnapshotCreate(
            project_id=test_project.id,
            target_type="scene",
            target_id=target_id,
            data=complex_data,
        )

        result = await snapshot_service.create_with_project(
            db_session, obj_in=snapshot_in, project_id=test_project.id
        )

        assert result.data == complex_data


class TestSnapshotServiceGetByProject:
    """Tests for snapshot_service.get_by_project."""

    @pytest.mark.asyncio
    async def test_get_by_project_empty(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_project returns empty list when no snapshots exist."""
        result = await snapshot_service.get_by_project(db_session, project_id=test_project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_project_with_snapshots(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_project returns snapshots for specific project."""
        target_id = uuid4()

        # Create snapshots
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"name": "Hero"},
            ),
            project_id=test_project.id,
        )
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="chapter",
                target_id=uuid4(),
                data={"title": "Chapter 1"},
            ),
            project_id=test_project.id,
        )

        result = await snapshot_service.get_by_project(db_session, project_id=test_project.id)
        assert len(result) == 2
        # Check that both types are present (order may vary due to timestamp resolution)
        target_types = {s.target_type for s in result}
        assert target_types == {"character", "chapter"}


class TestSnapshotServiceGetByTarget:
    """Tests for snapshot_service.get_by_target."""

    @pytest.mark.asyncio
    async def test_get_by_target(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_target returns snapshots for specific target."""
        target_id = uuid4()

        # Create snapshots for same target
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"name": "Hero v1"},
            ),
            project_id=test_project.id,
        )
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"name": "Hero v2"},
            ),
            project_id=test_project.id,
        )
        # Create snapshot for different target
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                data={"name": "Other"},
            ),
            project_id=test_project.id,
        )

        result = await snapshot_service.get_by_target(
            db_session, project_id=test_project.id, target_type="character", target_id=target_id
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_latest_by_target(self, db_session: AsyncSession, test_project: Project):
        """Test get_latest_by_target returns a snapshot for the target."""
        target_id = uuid4()

        # Create snapshots
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"version": 1},
            ),
            project_id=test_project.id,
        )
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"version": 2},
            ),
            project_id=test_project.id,
        )

        result = await snapshot_service.get_latest_by_target(
            db_session, project_id=test_project.id, target_type="character", target_id=target_id
        )
        assert result is not None
        assert result.target_type == "character"
        assert result.target_id == target_id
        assert "version" in result.data

    @pytest.mark.asyncio
    async def test_get_latest_by_target_not_found(self, db_session: AsyncSession, test_project: Project):
        """Test get_latest_by_target returns None when no snapshots exist."""
        target_id = uuid4()

        result = await snapshot_service.get_latest_by_target(
            db_session, project_id=test_project.id, target_type="character", target_id=target_id
        )
        assert result is None


class TestSnapshotServiceCreateSnapshot:
    """Tests for snapshot_service.create_snapshot."""

    @pytest.mark.asyncio
    async def test_create_snapshot_helper(self, db_session: AsyncSession, test_project: Project):
        """Test create_snapshot helper method."""
        target_id = uuid4()
        data = {"name": "Hero", "level": 5}

        result = await snapshot_service.create_snapshot(
            db_session,
            project_id=test_project.id,
            target_type="character",
            target_id=target_id,
            data=data,
        )

        assert result.id is not None
        assert result.target_type == "character"
        assert result.data == data


class TestSnapshotServiceGetSnapshotData:
    """Tests for snapshot_service.get_snapshot_data."""

    @pytest.mark.asyncio
    async def test_get_snapshot_data(self, db_session: AsyncSession, test_project: Project):
        """Test get_snapshot_data returns the stored data."""
        target_id = uuid4()
        data = {"content": "Chapter text", "word_count": 1000}
        snapshot = await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="chapter",
                target_id=target_id,
                data=data,
            ),
            project_id=test_project.id,
        )

        result = await snapshot_service.get_snapshot_data(db_session, snapshot_id=snapshot.id)

        assert result == data

    @pytest.mark.asyncio
    async def test_get_snapshot_data_not_found(self, db_session: AsyncSession):
        """Test get_snapshot_data returns None for non-existent snapshot."""
        result = await snapshot_service.get_snapshot_data(db_session, snapshot_id=uuid4())
        assert result is None


class TestSnapshotServiceCount:
    """Tests for snapshot_service count operations."""

    @pytest.mark.asyncio
    async def test_count_by_project(self, db_session: AsyncSession, test_project: Project):
        """Test count_by_project returns correct count."""
        target_id = uuid4()

        # Create snapshots
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={},
            ),
            project_id=test_project.id,
        )
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="chapter",
                target_id=uuid4(),
                data={},
            ),
            project_id=test_project.id,
        )

        count = await snapshot_service.count_by_project(db_session, project_id=test_project.id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_by_project_with_type_filter(self, db_session: AsyncSession, test_project: Project):
        """Test count_by_project with target_type filter."""
        target_id = uuid4()

        # Create snapshots
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={},
            ),
            project_id=test_project.id,
        )
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="chapter",
                target_id=uuid4(),
                data={},
            ),
            project_id=test_project.id,
        )

        count = await snapshot_service.count_by_project(
            db_session, project_id=test_project.id, target_type="character"
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_count_by_target(self, db_session: AsyncSession, test_project: Project):
        """Test count_by_target returns correct count for specific target."""
        target_id = uuid4()

        # Create snapshots for same target
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"v": 1},
            ),
            project_id=test_project.id,
        )
        await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"v": 2},
            ),
            project_id=test_project.id,
        )

        count = await snapshot_service.count_by_target(
            db_session, project_id=test_project.id, target_type="character", target_id=target_id
        )
        assert count == 2


class TestSnapshotServiceGet:
    """Tests for snapshot_service.get."""

    @pytest.mark.asyncio
    async def test_get_existing(self, db_session: AsyncSession, test_project: Project):
        """Test getting an existing snapshot by ID."""
        target_id = uuid4()
        snapshot = await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"name": "Hero"},
            ),
            project_id=test_project.id,
        )

        result = await snapshot_service.get(db_session, id=snapshot.id)

        assert result.id == snapshot.id
        assert result.target_type == "character"

    @pytest.mark.asyncio
    async def test_get_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent snapshot raises NotFoundException."""
        non_existent_id = uuid4()

        with pytest.raises(NotFoundException, match="Snapshot not found"):
            await snapshot_service.get(db_session, id=non_existent_id)


class TestSnapshotServiceUpdate:
    """Tests for snapshot_service.update."""

    @pytest.mark.asyncio
    async def test_update_snapshot_data(self, db_session: AsyncSession, test_project: Project):
        """Test updating snapshot data."""
        target_id = uuid4()
        snapshot = await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={"name": "Hero", "level": 1},
            ),
            project_id=test_project.id,
        )

        updated = await snapshot_service.update(
            db_session,
            db_obj=snapshot,
            obj_in=SnapshotUpdate(data={"name": "Hero", "level": 2, "class": "Warrior"}),
        )

        assert updated.id == snapshot.id
        assert updated.data == {"name": "Hero", "level": 2, "class": "Warrior"}


class TestSnapshotServiceDelete:
    """Tests for snapshot_service delete operations."""

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session: AsyncSession, test_project: Project):
        """Test deleting a snapshot successfully."""
        target_id = uuid4()
        snapshot = await snapshot_service.create_with_project(
            db_session,
            obj_in=SnapshotCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                data={},
            ),
            project_id=test_project.id,
        )
        snapshot_id = snapshot.id

        deleted = await snapshot_service.delete(db_session, id=snapshot_id)

        assert deleted.id == snapshot_id

        # Verify snapshot is actually deleted
        with pytest.raises(NotFoundException, match="Snapshot not found"):
            await snapshot_service.get(db_session, id=snapshot_id)
