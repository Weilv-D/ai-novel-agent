"""Integration tests for Memory service layer with real DB."""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestException
from app.models.memory import Memory
from app.models.project import Project
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

        Uses Mock to simulate vector search without pgvector dependency.
        """
        from unittest.mock import AsyncMock, patch

        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
            genre="fantasy",
            status="drafting",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        memory = Memory(
            id=uuid.uuid4(),
            project_id=project.id,
            memory_type="fact",
            content="Test fact",
            embedding=None,
        )
        db_session.add(memory)
        await db_session.commit()

        with patch.object(
            memory_service,
            "search_by_embedding",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            result, count = await memory_service.search_by_embedding(
                db_session,
                project_id=project.id,
                search_params=VectorSearchRequest(
                    query_embedding=[0.1] * EMBEDDING_DIMENSION,
                    limit=10,
                    threshold=0.7,
                ),
            )
            assert result == []
            assert count == 0

    @pytest.mark.asyncio
    async def test_search_by_embedding_with_threshold(self, db_session: AsyncSession):
        """Test search with similarity threshold.

        Uses Mock to simulate vector search without pgvector dependency.
        """
        from unittest.mock import AsyncMock, patch

        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
            genre="fantasy",
            status="drafting",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        memory = Memory(
            id=uuid.uuid4(),
            project_id=project.id,
            memory_type="fact",
            content="Test fact",
            embedding=[0.9] + [0.0] * (EMBEDDING_DIMENSION - 1),
        )
        db_session.add(memory)
        await db_session.commit()

        mock_matches = [
            {
                "id": memory.id,
                "memory_type": "fact",
                "content": "Test fact",
                "meta": {},
                "similarity": 0.95,
            }
        ]

        with patch.object(
            memory_service,
            "search_by_embedding",
            new_callable=AsyncMock,
            return_value=(mock_matches, 1),
        ):
            result, count = await memory_service.search_by_embedding(
                db_session,
                project_id=project.id,
                search_params=VectorSearchRequest(
                    query_embedding=[0.1] * EMBEDDING_DIMENSION,
                    limit=5,
                    threshold=0.7,
                    memory_type="fact",
                ),
            )
            assert len(result) == 1
            assert count == 1
            assert result[0]["similarity"] >= 0.7


class TestMemoryServiceCache:
    """Tests for memory vector-search cache behavior."""

    @pytest.mark.asyncio
    async def test_search_by_embedding_returns_cached_result(self) -> None:
        """Vector search should return cache hits without querying the database."""
        from unittest.mock import AsyncMock, patch

        db_session = AsyncMock()
        project_id = uuid.uuid4()
        cached_matches = [
            {
                "id": str(uuid.uuid4()),
                "memory_type": "fact",
                "content": "Cached fact",
                "meta": {},
                "similarity": 0.91,
            }
        ]

        with patch("app.services.memory.cache_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"matches": cached_matches, "total_count": 1}

            result, count = await memory_service.search_by_embedding(
                db_session,
                project_id=project_id,
                search_params=VectorSearchRequest(
                    query_embedding=[0.1] * EMBEDDING_DIMENSION,
                    limit=10,
                    threshold=0.7,
                ),
            )

        assert result == cached_matches
        assert count == 1
        db_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_by_embedding_executes_query_and_caches_results(self) -> None:
        """A cache miss should execute the vector query, convert rows, and cache the result."""
        from unittest.mock import AsyncMock, patch

        class FakeQueryResult:
            def __init__(self, *, rows=None, scalar_value=None):
                self._rows = rows or []
                self._scalar_value = scalar_value

            def all(self):
                return self._rows

            def scalar(self):
                return self._scalar_value

        db_session = AsyncMock()
        project_id = uuid.uuid4()
        row = SimpleNamespace(
            id=uuid.uuid4(),
            memory_type="fact",
            content="命中的事实",
            meta={"chapter": 1},
            similarity=0.93,
        )
        db_session.execute.side_effect = [FakeQueryResult(rows=[row])]

        with patch("app.services.memory.cache_service.get", new_callable=AsyncMock) as mock_get:
            with patch("app.services.memory.cache_service.set", new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                result, count = await memory_service.search_by_embedding(
                    db_session,
                    project_id=project_id,
                    search_params=VectorSearchRequest(
                        query_embedding=[0.1] * EMBEDDING_DIMENSION,
                        limit=5,
                        threshold=0.7,
                        memory_type="fact",
                    ),
                )

        assert count == 1
        assert result == [
            {
                "id": row.id,
                "memory_type": "fact",
                "content": "命中的事实",
                "meta": {"chapter": 1},
                "similarity": 0.93,
            }
        ]
        assert db_session.execute.await_count == 1
        mock_set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_by_embedding_applies_meta_and_related_filters(self) -> None:
        """Metadata, related ids, and scope filters should be enforced after vector retrieval."""
        from unittest.mock import AsyncMock, patch

        class FakeQueryResult:
            def __init__(self, *, rows=None):
                self._rows = rows or []

            def all(self):
                return self._rows

        db_session = AsyncMock()
        project_id = uuid.uuid4()
        character_id = uuid.uuid4()
        world_setting_id = uuid.uuid4()
        chapter_id = uuid.uuid4()
        matching_row = SimpleNamespace(
            id=uuid.uuid4(),
            memory_type="fact",
            content="匹配事实",
            meta={
                "fact_kind": "timeline",
                "character_ids": [str(character_id)],
                "world_setting_ids": [str(world_setting_id)],
                "chapter_id": str(chapter_id),
            },
            similarity=0.95,
        )
        skipped_row = SimpleNamespace(
            id=uuid.uuid4(),
            memory_type="fact",
            content="不匹配事实",
            meta={
                "fact_kind": "setting",
                "character_ids": [str(uuid.uuid4())],
                "world_setting_ids": [str(uuid.uuid4())],
                "chapter_id": str(uuid.uuid4()),
            },
            similarity=0.99,
        )
        db_session.execute.side_effect = [FakeQueryResult(rows=[matching_row, skipped_row])]

        with patch("app.services.memory.cache_service.get", new_callable=AsyncMock) as mock_get:
            with patch("app.services.memory.cache_service.set", new_callable=AsyncMock):
                mock_get.return_value = None

                result, count = await memory_service.search_by_embedding(
                    db_session,
                    project_id=project_id,
                    search_params=VectorSearchRequest(
                        query_embedding=[0.1] * EMBEDDING_DIMENSION,
                        limit=5,
                        threshold=0.7,
                        memory_type="fact",
                        meta_filters={"fact_kind": "timeline"},
                        related_character_ids=[character_id],
                        related_world_setting_ids=[world_setting_id],
                        scope={"chapter_id": chapter_id},
                    ),
                )

        assert count == 1
        assert len(result) == 1
        assert result[0]["content"] == "匹配事实"

    @pytest.mark.asyncio
    async def test_upsert_fact_merges_by_fingerprint(self, db_session: AsyncSession):
        """Upserting the same fact fingerprint should merge into the existing row."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Fact Project", genre="Fantasy"),
        )

        first = await memory_service.upsert_fact(
            db_session,
            project_id=project.id,
            memory_type="fact",
            content="苏砚在第三章夜探山门。",
            meta={
                "fact_kind": "timeline",
                "chapter_id": "chapter-3",
                "character_ids": ["char-1"],
            },
        )
        second = await memory_service.upsert_fact(
            db_session,
            project_id=project.id,
            memory_type="fact",
            content="苏砚在第三章夜探山门。",
            meta={
                "fact_kind": "timeline",
                "chapter_id": "chapter-3",
                "character_ids": ["char-1"],
                "timeline_marker": "night",
            },
        )

        all_facts = await memory_service.get_by_project(db_session, project_id=project.id, memory_type="fact")

        assert first.id == second.id
        assert len(all_facts) == 1
        assert all_facts[0].meta["timeline_marker"] == "night"

    @pytest.mark.asyncio
    async def test_create_with_project_invalidates_search_cache(self, db_session: AsyncSession):
        """Creating a memory should invalidate cached vector search results for the project."""
        from unittest.mock import AsyncMock, patch

        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        with patch("app.services.memory.cache_service.invalidate_pattern", new_callable=AsyncMock) as mock_invalidate:
            await memory_service.create_with_project(
                db_session,
                obj_in=MemoryCreate(
                    project_id=project.id,
                    memory_type="fact",
                    content="New fact",
                ),
                project_id=project.id,
            )

        mock_invalidate.assert_awaited_once_with(f"vsearch:{project.id}:*")

    @pytest.mark.asyncio
    async def test_update_invalidates_search_cache(self, db_session: AsyncSession):
        """Updating a memory should invalidate cached vector search results for the project."""
        from unittest.mock import AsyncMock, patch

        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        memory = await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="Original fact",
            ),
            project_id=project.id,
        )

        with patch("app.services.memory.cache_service.invalidate_pattern", new_callable=AsyncMock) as mock_invalidate:
            await memory_service.update(
                db_session,
                db_obj=memory,
                obj_in=MemoryUpdate(content="Updated fact"),
            )

        mock_invalidate.assert_awaited_once_with(f"vsearch:{project.id}:*")

    @pytest.mark.asyncio
    async def test_update_with_dict_embedding_validates_dimension_and_invalidates_cache(self, db_session: AsyncSession):
        """Dict-based updates should validate embeddings before delegating to CRUDBase.update()."""
        from unittest.mock import AsyncMock, patch

        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        memory = await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="Original fact",
            ),
            project_id=project.id,
        )

        with patch("app.services.memory.cache_service.invalidate_pattern", new_callable=AsyncMock) as mock_invalidate:
            updated = await memory_service.update(
                db_session,
                db_obj=memory,
                obj_in={
                    "content": "Updated via dict",
                    "embedding": [0.4] * EMBEDDING_DIMENSION,
                },
            )

        assert updated.content == "Updated via dict"
        assert updated.embedding is not None
        mock_invalidate.assert_awaited_once_with(f"vsearch:{project.id}:*")

    @pytest.mark.asyncio
    async def test_delete_invalidates_search_cache(self, db_session: AsyncSession):
        """Deleting a memory should invalidate cached vector search results for the project."""
        from unittest.mock import AsyncMock, patch

        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        memory = await memory_service.create_with_project(
            db_session,
            obj_in=MemoryCreate(
                project_id=project.id,
                memory_type="fact",
                content="Disposable fact",
            ),
            project_id=project.id,
        )

        with patch("app.services.memory.cache_service.invalidate_pattern", new_callable=AsyncMock) as mock_invalidate:
            await memory_service.delete(db_session, id=memory.id)

        mock_invalidate.assert_awaited_once_with(f"vsearch:{project.id}:*")
