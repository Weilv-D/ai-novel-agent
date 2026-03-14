"""Memory API routes for narrative facts and vector embeddings."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.memory import Memory
from app.schemas.memory import (
    MemoryCreate,
    MemoryMatch,
    MemoryResponse,
    MemoryUpdate,
    VectorSearchRequest,
    VectorSearchResponse,
)
from app.services.llm import llm_service
from app.services.memory import memory_service

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    *,
    db: AsyncSession = Depends(get_db),
    memory_in: MemoryCreate,
) -> Memory:
    """Create a new memory with optional embedding.

    If auto_embed is True, automatically generates the embedding from content.
    """
    # Auto-generate embedding if requested and not already provided
    if memory_in.auto_embed and not memory_in.embedding:
        memory_in.embedding = await llm_service.embed_single(memory_in.content)

    return await memory_service.create_with_project(
        db, obj_in=memory_in, project_id=memory_in.project_id
    )


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    memory_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Memory]:
    """List all memories for a project, optionally filtered by type."""
    return await memory_service.get_by_project(
        db, project_id=project_id, memory_type=memory_type, skip=skip, limit=limit
    )


@router.get("/type/{memory_type}", response_model=list[MemoryResponse])
async def list_memories_by_type(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    memory_type: str,
    skip: int = 0,
    limit: int = 100,
) -> list[Memory]:
    """List memories of a specific type for a project."""
    return await memory_service.get_by_type(
        db, project_id=project_id, memory_type=memory_type, skip=skip, limit=limit
    )


@router.get("/count", response_model=dict[str, Any])
async def count_memories(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    memory_type: str | None = None,
) -> dict[str, Any]:
    """Count memories for a project, optionally filtered by type."""
    count = await memory_service.count_by_project(db, project_id=project_id, memory_type=memory_type)
    return {"count": count, "project_id": str(project_id), "memory_type": memory_type}


@router.post("/search", response_model=VectorSearchResponse)
async def search_memories_by_embedding(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request: VectorSearchRequest,
) -> VectorSearchResponse:
    """Search memories by vector embedding similarity using cosine distance.

    Returns memories with embeddings most similar to the query embedding.
    """
    matches, total_count = await memory_service.search_by_embedding(
        db, project_id=project_id, search_params=request
    )

    memory_matches = [MemoryMatch(**match) for match in matches]

    return VectorSearchResponse(
        matches=memory_matches,
        total_count=total_count,
        search_summary=f"Found {len(matches)} memories with similarity >= {request.threshold}",
    )


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    *,
    db: AsyncSession = Depends(get_db),
    memory_id: UUID,
) -> Memory:
    """Get a memory by ID."""
    return await memory_service.get(db, id=memory_id)


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    *,
    db: AsyncSession = Depends(get_db),
    memory_id: UUID,
    memory_in: MemoryUpdate,
) -> Memory:
    """Update a memory (content, memory_type, meta, or embedding).

    If auto_embed is True and content is provided, automatically regenerates the embedding.
    """
    memory = await memory_service.get(db, id=memory_id)

    # Auto-generate embedding if requested and content is being updated
    if memory_in.auto_embed and memory_in.content:
        memory_in.embedding = await llm_service.embed_single(memory_in.content)

    return await memory_service.update(db, db_obj=memory, obj_in=memory_in)


@router.delete("/{memory_id}", response_model=MemoryResponse)
async def delete_memory(
    *,
    db: AsyncSession = Depends(get_db),
    memory_id: UUID,
) -> Memory:
    """Delete a memory by ID."""
    return await memory_service.delete(db, id=memory_id)
