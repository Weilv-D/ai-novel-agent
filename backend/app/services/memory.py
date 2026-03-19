"""Memory service layer with vector similarity search."""

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.cache import cache_service
from app.core.config import get_settings
from app.core.exceptions import BadRequestException
from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryUpdate, VectorSearchRequest
from app.services.base import CRUDBase

EMBEDDING_DIMENSION = get_settings().embedding_dimension


class CRUDMemory(CRUDBase[Memory, MemoryCreate, MemoryUpdate]):
    """CRUD operations for Memory model with vector search."""

    SEARCH_CACHE_TTL_SECONDS = 300

    @staticmethod
    def _validate_embedding(embedding: list[float] | None) -> None:
        """Validate an embedding before persisting or querying."""
        if embedding is None:
            return
        if len(embedding) != EMBEDDING_DIMENSION:
            raise BadRequestException(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(embedding)}"
            )

    @staticmethod
    def _build_search_cache_key(project_id: Any, search_params: VectorSearchRequest) -> str:
        """Build a stable cache key for vector search results."""
        payload: dict[str, Any] = {
            "query_embedding": search_params.query_embedding,
            "limit": search_params.limit,
            "threshold": search_params.threshold,
            "memory_type": search_params.memory_type,
            "meta_filters": search_params.meta_filters,
            "related_character_ids": [str(item) for item in search_params.related_character_ids],
            "related_world_setting_ids": [str(item) for item in search_params.related_world_setting_ids],
            "scope": {key: str(value) for key, value in search_params.scope.items()},
        }
        return f"vsearch:{project_id}:{cache_service.build_hash(payload)}"

    @staticmethod
    def _meta_matches(meta: dict[str, Any], search_params: VectorSearchRequest) -> bool:
        """Apply metadata filters to one memory row."""
        for key, expected in search_params.meta_filters.items():
            actual = meta.get(key)
            if isinstance(expected, list):
                actual_values = actual if isinstance(actual, list) else [actual]
                if not all(item in actual_values for item in expected):
                    return False
                continue
            if actual != expected:
                return False

        if search_params.related_character_ids:
            actual_ids = {
                str(item)
                for item in (meta.get("character_ids") or [])
                if str(item).strip()
            }
            if not actual_ids.intersection({str(item) for item in search_params.related_character_ids}):
                return False

        if search_params.related_world_setting_ids:
            actual_ids = {
                str(item)
                for item in (meta.get("world_setting_ids") or [])
                if str(item).strip()
            }
            if not actual_ids.intersection({str(item) for item in search_params.related_world_setting_ids}):
                return False

        for key, scope_expected in search_params.scope.items():
            actual = meta.get(key)
            if actual is None or str(actual) != str(scope_expected):
                return False
        return True

    @staticmethod
    def build_fact_fingerprint(
        *,
        content: str,
        meta: dict[str, Any],
    ) -> str:
        """Build a stable fingerprint for deduplicating narrative facts."""
        payload = {
            "content": " ".join(content.split()).strip().lower(),
            "fact_kind": meta.get("fact_kind"),
            "chapter_id": str(meta.get("chapter_id") or ""),
            "scene_id": str(meta.get("scene_id") or ""),
            "volume_id": str(meta.get("volume_id") or ""),
            "character_ids": sorted(str(item) for item in meta.get("character_ids", []) if str(item).strip()),
            "world_setting_ids": sorted(
                str(item) for item in meta.get("world_setting_ids", []) if str(item).strip()
            ),
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    async def _invalidate_project_search_cache(self, project_id: Any) -> None:
        """Invalidate cached vector search results for a project."""
        await cache_service.invalidate_pattern(f"vsearch:{project_id}:*")

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
        cache_key = self._build_search_cache_key(project_id, search_params)
        cached_result = await cache_service.get(cache_key)
        if isinstance(cached_result, dict):
            cached_matches = cached_result.get("matches")
            cached_total_count = cached_result.get("total_count")
            if isinstance(cached_matches, list) and isinstance(cached_total_count, int):
                return cached_matches, cached_total_count

        # Import Vector for distance calculation
        from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
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
        )

        result = await db.execute(stmt)
        rows = result.all()

        # Convert to list of dicts with similarity
        matches = []
        for row in rows:
            meta = dict(row.meta or {})
            if not self._meta_matches(meta, search_params):
                continue
            matches.append(
                {
                    "id": row.id,
                    "memory_type": row.memory_type,
                    "content": row.content,
                    "meta": meta,
                    "similarity": float(row.similarity),
                }
            )
        total_count = len(matches)
        matches = matches[: search_params.limit]

        await cache_service.set(
            cache_key,
            {"matches": matches, "total_count": total_count},
            ttl=self.SEARCH_CACHE_TTL_SECONDS,
        )

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
        await self._invalidate_project_search_cache(project_id)
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
        updated = await super().update(db, db_obj=db_obj, obj_in=obj_in)
        await self._invalidate_project_search_cache(updated.project_id)
        return updated

    async def delete(self, db: AsyncSession, *, id: Any) -> Memory:
        """Delete a memory and invalidate project vector-search cache."""
        memory = await self.get(db, id)
        project_id = memory.project_id
        await db.delete(memory)
        await db.flush()
        await self._invalidate_project_search_cache(project_id)
        return memory

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

    async def upsert_fact(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        memory_type: str,
        content: str,
        meta: dict[str, Any],
        embedding: list[float] | None = None,
    ) -> Memory:
        """Upsert one memory fact using the normalized fingerprint."""
        next_meta = dict(meta)
        fingerprint = str(next_meta.get("fingerprint") or self.build_fact_fingerprint(content=content, meta=next_meta))
        next_meta["fingerprint"] = fingerprint
        existing_memories = await self.get_by_project(db, project_id=project_id, memory_type=memory_type, limit=1000)
        for memory in existing_memories:
            current_meta = memory.meta or {}
            if current_meta.get("fingerprint") != fingerprint:
                continue
            merged_meta = dict(current_meta)
            merged_meta.update(next_meta)
            memory.content = content
            memory.meta = merged_meta
            if embedding is not None:
                memory.embedding = embedding
            await db.flush()
            await db.refresh(memory)
            await self._invalidate_project_search_cache(project_id)
            return memory

        return await self.create_with_project(
            db,
            project_id=project_id,
            obj_in=MemoryCreate(
                project_id=project_id,
                memory_type=memory_type,
                content=content,
                meta=next_meta,
                embedding=embedding,
                auto_embed=False,
            ),
        )

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
