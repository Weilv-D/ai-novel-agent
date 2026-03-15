"""Integration tests for Memory service layer with real DB."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestException
from app.schemas.memory import MemoryCreate, MemoryUpdate, VectorSearchRequest
from app.schemas.project import ProjectCreate
from app.services.memory import memory_service
from app.services.project import project_service

EMBEDDING_DIMENSION = get_settings().embedding_dimension


class TestMemoryServiceGetByProject:
    """Tests for memory_service.get_by_project with real database."""

    @pytest.mark.asyncio
    async def test_get_by_project_empty(self, db_session: AsyncSession):
        """Test get_by_project returns empty list when no memories exist."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        result = await memory_service.get_by_project(db_session, project_id=project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_project_with_memories(self, db_session: AsyncSession):
        """Test get_by_project returns memories for specific project."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        other_project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Other Project", genre="Sci-Fi"),
        )

        # Create memories for different projects
        mem1 = await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="episode",
                content="Memory 1",
            ),
            project_id=project.id,
        )
        mem2 = await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="Memory 2",
            ),
            project_id=project.id,
        )
        await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=other_project.id,
                memory_type="semantic",
                content="Other memory",
            ),
            project_id=other_project.id,
        )

        # Get memories for project
        result = await memory_service.get_by_project(db_session, project_id=project.id)
        assert len(result) == 2
        mem_ids = {m.id for m in result}
        assert mem1.id in mem_ids
        assert mem2.id in mem_ids

    @pytest.mark.asyncio
    async def test_get_by_project_with_type_filter(self, db_session: AsyncSession):
        """Test get_by_project filtered by memory type."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        # Create memories of different types
        await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="episode",
                content="Episode memory",
            ),
            project_id=project.id,
        )
        await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="Fact memory",
            ),
            project_id=project.id,
        )

        # Filter by type
        result = await memory_service.get_by_project(
            db_session, project_id=project.id, memory_type="fact"
        )
        assert len(result) == 1
        assert result[0].memory_type == "fact"


class TestMemoryServiceCreateWithProject:
    """Tests for memory_service.create_with_project with real database."""

    @pytest.mark.asyncio
    async def test_create_with_project_valid(self, db_session: AsyncSession):
        """Test creating a memory with valid data."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        mem_in = MemoryCreate(
            project_id=project.id,
            memory_type="episode",
            content="The hero began their journey.",
            meta={"chapter": 1},
        )

        result = await memory_service.create_with_project(
            db_session,
            obj_in=mem_in,
            project_id=project.id,
        )

        assert result.id is not None
        assert result.memory_type == "episode"
        assert result.content == "The hero began their journey."
        assert result.project_id == project.id
        assert result.meta["chapter"] == 1

    @pytest.mark.asyncio
    async def test_create_with_embedding(self, db_session: AsyncSession):
        """Test creating a memory with vector embedding."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        embedding = [0.1] * EMBEDDING_DIMENSION
        mem_in = MemoryCreate(
            project_id=project.id,
            memory_type="semantic",
            content="Magic exists in this world.",
            embedding=embedding,
        )

        result = await memory_service.create_with_project(
            db_session,
            obj_in=mem_in,
            project_id=project.id,
        )

        assert result.embedding is not None
        assert len(result.embedding) == EMBEDDING_DIMENSION


class TestMemoryServiceUpdate:
    """Tests for memory_service.update with real database."""

    @pytest.mark.asyncio
    async def test_update_partial(self, db_session: AsyncSession):
        """Test updating specific fields of a memory."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        memory = await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="Original content",
            ),
            project_id=project.id,
        )

        updated = await memory_service.update(
            db_session,
            db_obj=memory,
            obj_in=MemoryUpdate(content="Updated content"),
        )

        assert updated.id == memory.id
        assert updated.content == "Updated content"
        assert updated.memory_type == "fact"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_with_embedding(self, db_session: AsyncSession):
        """Test updating memory with new embedding."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        memory = await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="A fact",
            ),
            project_id=project.id,
        )

        new_embedding = [0.2] * EMBEDDING_DIMENSION
        updated = await memory_service.update(
            db_session,
            db_obj=memory,
            obj_in=MemoryUpdate(embedding=new_embedding),
        )

        assert updated.embedding is not None
        assert len(updated.embedding) == EMBEDDING_DIMENSION
        assert updated.embedding[0] == 0.2


class TestMemoryServiceCount:
    """Tests for memory_service.count_by_project."""

    @pytest.mark.asyncio
    async def test_count_by_project(self, db_session: AsyncSession):
        """Test counting memories for a project."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        # Create some memories
        for i in range(3):
            await memory_service.create_with_project(
                db_session,
                obj_in=MemoryCreate(
                    project_id=project.id,
                    memory_type="fact",
                    content=f"Fact {i}",
                ),
                project_id=project.id,
            )

        count = await memory_service.count_by_project(db_session, project_id=project.id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_by_project_with_type_filter(self, db_session: AsyncSession):
        """Test counting memories filtered by type."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        # Create memories of different types
        await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="episode",
                content="Episode",
            ),
            project_id=project.id,
        )
        await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="Fact 1",
            ),
            project_id=project.id,
        )
        await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="Fact 2",
            ),
            project_id=project.id,
        )

        count = await memory_service.count_by_project(
            db_session, project_id=project.id, memory_type="fact"
        )
        assert count == 2


class TestMemoryServiceSearchByEmbedding:
    """Tests for memory_service.search_by_embedding."""

    @pytest.mark.asyncio
    async def test_search_by_embedding_invalid_dimension(self, db_session: AsyncSession):
        """Test search with invalid embedding dimension (no pgvector required)."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        with pytest.raises(BadRequestException) as exc_info:
            await memory_service.search_by_embedding(
                db_session,
                project_id=project.id,
                search_params=VectorSearchRequest.model_construct(
                    query_embedding=[0.1] * 100,
                    limit=10,
                    threshold=0.7,
                    memory_type=None,
                ),
            )

        assert str(EMBEDDING_DIMENSION) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_by_embedding_no_results(self, db_session: AsyncSession):
        """Test search when no memories have embeddings.

        Note: Skipped in SQLite test environment - requires PostgreSQL with pgvector.
        """
        pytest.skip("Requires PostgreSQL with pgvector extension (test uses SQLite)")

    @pytest.mark.asyncio
    async def test_search_by_embedding_with_threshold(self, db_session: AsyncSession):
        """Test search with similarity threshold.

        Note: Skipped in SQLite test environment - requires PostgreSQL with pgvector.
        """
        pytest.skip("Requires PostgreSQL with pgvector extension (test uses SQLite)")
