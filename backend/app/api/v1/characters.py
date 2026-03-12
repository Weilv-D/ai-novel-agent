"""Character API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.character import Character
from app.schemas.character import CharacterCreate, CharacterResponse, CharacterUpdate
from app.services.character import character_service

router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    *,
    db: AsyncSession = Depends(get_db),
    character_in: CharacterCreate,
) -> Character:
    """Create a new character."""
    # project_id comes from request body
    return await character_service.create_with_project(
        db, obj_in=character_in, project_id=character_in.project_id
    )


@router.get("/project/{project_id}", response_model=list[CharacterResponse])
async def list_characters_by_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Character]:
    """List all characters for a specific project."""
    return await character_service.get_by_project(
        db, project_id=project_id, skip=skip, limit=limit
    )


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    *,
    db: AsyncSession = Depends(get_db),
    character_id: UUID,
) -> Character:
    """Get a character by ID."""
    return await character_service.get(db, id=character_id)


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    *,
    db: AsyncSession = Depends(get_db),
    character_id: UUID,
    character_in: CharacterUpdate,
) -> Character:
    """Update a character."""
    character = await character_service.get(db, id=character_id)
    return await character_service.update(db, db_obj=character, obj_in=character_in)


@router.delete("/{character_id}", response_model=CharacterResponse)
async def delete_character(
    *,
    db: AsyncSession = Depends(get_db),
    character_id: UUID,
) -> Character:
    """Delete a character."""
    return await character_service.delete(db, id=character_id)
