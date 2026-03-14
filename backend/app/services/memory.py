"""Memory service layer with vector similarity search."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.config import get_settings
from app.core.exceptions import BadRequestException
from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryUpdate, VectorSearchRequest
from app.services.base import CRUDBase

EMBEDDING_DIMENSION = get_settings().embedding_dimension


class CRUDMemory(CRUDBase[Memory, MemoryCreate, MemoryUpdate]):
    """CRUD operations for Memory model with vector search."""

    @staticmethod
    def _validate_embedding(embedding: list[float] | None) -> None:
        """Validate an embedding before persisting or querying."""
        if embedding is None:
            return
        if len(embedding) != EMBEDDING_DIMENSION:
            raise BadRequestException(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(embedding)}"
            )

    async def get_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        skip: int = 0,
        limit: int = 100,
        memory_type: str | None = None,
    ) -> list[Memory]:
        """Get all memories for a project, optionally filtered by type."""
        stmt = select(Memory).where(Memory.project_id == project_id)
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)
        stmt = stmt.order_by(Memory.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def search_by_embedding(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        search_params: VectorSearchRequest,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search memories by vector embedding similarity using cosine distance.

        Returns:
            Tuple of (matches_with_similarity, total_count)
            Matches include id, memory_type, content, meta, and similarity score
        """
        # Validate embedding dimension
        self._validate_embedding(search_params.query_embedding)

        # Import Vector for distance calculation
        from pgvector.sqlalchemy import Vector
        from sqlalchemy import cast

        # Build query with cosine distance
        # Cosine distance = 1 - cosine_similarity, so we invert the threshold
        query_embedding = search_params.query_embedding
        embedding_col = Memory.embedding

        # Calculate similarity expression for reuse
        similarity_expr = 1 - func.cosine_distance(
            embedding_col,
            cast(query_embedding, Vector(EMBEDDING_DIMENSION)),
        )

        # Build base query with similarity calculation
        base_query = (
            select(
                Memory.id,
                Memory.memory_type,
                Memory.content,
                Memory.meta,
                similarity_expr.label("similarity"),
            )
            .where(Memory.project_id == project_id)
            .where(Memory.embedding.isnot(None))
        )

        # Optional memory type filter
        if search_params.memory_type:
            base_query = base_query.where(Memory.memory_type == search_params.memory_type)

        # Use subquery to enable filtering by calculated similarity
        memory_subquery = base_query.subquery()

        # Final query filters by threshold and orders by similarity
        stmt = (
            select(memory_subquery)
            .where(memory_subquery.c.similarity >= search_params.threshold)
            .order_by(memory_subquery.c.similarity.desc())
            .limit(search_params.limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        # Convert to list of dicts with similarity
        matches = [
            {
                "id": row.id,
                "memory_type": row.memory_type,
                "content": row.content,
                "meta": row.meta,
                "similarity": float(row.similarity),
            }
            for row in rows
        ]

        # Get total count of potential matches (without threshold or limit)
        count_stmt = (
            select(func.count())
            .select_from(Memory)
            .where(Memory.project_id == project_id)
            .where(Memory.embedding.isnot(None))
        )
        if search_params.memory_type:
            count_stmt = count_stmt.where(Memory.memory_type == search_params.memory_type)

        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar() or 0

        return matches, total_count

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: MemoryCreate,
        project_id: Any,
    ) -> Memory:
        """Create a new memory for a specific project."""
        self._validate_embedding(obj_in.embedding)
        obj_dict = obj_in.model_dump(exclude={"project_id", "auto_embed"})
        db_obj = Memory(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Memory,
        obj_in: MemoryUpdate | dict[str, Any],
    ) -> Memory:
        """Update a memory while enforcing embedding dimension consistency."""
        if isinstance(obj_in, dict):
            self._validate_embedding(obj_in.get("embedding"))
        else:
            self._validate_embedding(obj_in.embedding)
        return await super().update(db, db_obj=db_obj, obj_in=obj_in)

    async def get_by_type(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        memory_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Memory]:
        """Get memories of a specific type for a project."""
        result = await db.execute(
            select(Memory)
            .where(Memory.project_id == project_id, Memory.memory_type == memory_type)
            .order_by(Memory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_project(
        self, db: AsyncSession, *, project_id: Any, memory_type: str | None = None
    ) -> int:
        """Count memories for a project, optionally filtered by type."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Memory).where(Memory.project_id == project_id)
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)
        result = await db.execute(stmt)
        return result.scalar() or 0


# Singleton instance
memory_service = CRUDMemory(Memory)
