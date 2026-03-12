"""Chapter and Scene API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.chapter import Chapter, Scene, Volume
from app.schemas.chapter import (
    ChapterCreate,
    ChapterResponse,
    ChapterUpdate,
    SceneCreate,
    SceneResponse,
    SceneUpdate,
    VolumeCreate,
    VolumeResponse,
    VolumeUpdate,
)
from app.services.chapter import chapter_service, scene_service, volume_service

router = APIRouter(prefix="/chapters", tags=["chapters"])
scene_router = APIRouter(prefix="/scenes", tags=["scenes"])
volume_router = APIRouter(prefix="/volumes", tags=["volumes"])

# ============ Volume Routes ============


@volume_router.post("", response_model=VolumeResponse, status_code=status.HTTP_201_CREATED)
async def create_volume(
    *,
    db: AsyncSession = Depends(get_db),
    volume_in: VolumeCreate,
) -> Volume:
    """Create a new volume."""
    return await volume_service.create_with_project(
        db, obj_in=volume_in, project_id=volume_in.project_id
    )


@volume_router.get("/project/{project_id}", response_model=list[VolumeResponse])
async def list_volumes_by_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Volume]:
    """List all volumes for a specific project."""
    return await volume_service.get_by_project(db, project_id=project_id, skip=skip, limit=limit)


@volume_router.get("/{volume_id}", response_model=VolumeResponse)
async def get_volume(
    *,
    db: AsyncSession = Depends(get_db),
    volume_id: UUID,
) -> Volume:
    """Get a volume by ID."""
    return await volume_service.get(db, id=volume_id)


@volume_router.patch("/{volume_id}", response_model=VolumeResponse)
async def update_volume(
    *,
    db: AsyncSession = Depends(get_db),
    volume_id: UUID,
    volume_in: VolumeUpdate,
) -> Volume:
    """Update a volume."""
    volume = await volume_service.get(db, id=volume_id)
    return await volume_service.update(db, db_obj=volume, obj_in=volume_in)


@volume_router.delete("/{volume_id}", response_model=VolumeResponse)
async def delete_volume(
    *,
    db: AsyncSession = Depends(get_db),
    volume_id: UUID,
) -> Volume:
    """Delete a volume."""
    return await volume_service.delete(db, id=volume_id)


# ============ Chapter Routes ============


@router.post("", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    *,
    db: AsyncSession = Depends(get_db),
    chapter_in: ChapterCreate,
) -> Chapter:
    """Create a new chapter."""
    return await chapter_service.create_with_project(
        db, obj_in=chapter_in, project_id=chapter_in.project_id
    )


@router.get("/project/{project_id}", response_model=list[ChapterResponse])
async def list_chapters_by_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Chapter]:
    """List all chapters for a specific project."""
    return await chapter_service.get_by_project(db, project_id=project_id, skip=skip, limit=limit)


@router.get("/volume/{volume_id}", response_model=list[ChapterResponse])
async def list_chapters_by_volume(
    *,
    db: AsyncSession = Depends(get_db),
    volume_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Chapter]:
    """List all chapters for a specific volume."""
    return await chapter_service.get_by_volume(db, volume_id=volume_id, skip=skip, limit=limit)


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    *,
    db: AsyncSession = Depends(get_db),
    chapter_id: UUID,
) -> Chapter:
    """Get a chapter by ID."""
    return await chapter_service.get(db, id=chapter_id)


@router.patch("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    *,
    db: AsyncSession = Depends(get_db),
    chapter_id: UUID,
    chapter_in: ChapterUpdate,
) -> Chapter:
    """Update a chapter."""
    chapter = await chapter_service.get(db, id=chapter_id)
    return await chapter_service.update(db, db_obj=chapter, obj_in=chapter_in)


@router.delete("/{chapter_id}", response_model=ChapterResponse)
async def delete_chapter(
    *,
    db: AsyncSession = Depends(get_db),
    chapter_id: UUID,
) -> Chapter:
    """Delete a chapter."""
    return await chapter_service.delete(db, id=chapter_id)


# ============ Scene Routes ============


@scene_router.post("", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
async def create_scene(
    *,
    db: AsyncSession = Depends(get_db),
    scene_in: SceneCreate,
) -> Scene:
    """Create a new scene."""
    return await scene_service.create_with_chapter(
        db, obj_in=scene_in, chapter_id=scene_in.chapter_id
    )


@scene_router.get("/chapter/{chapter_id}", response_model=list[SceneResponse])
async def list_scenes_by_chapter(
    *,
    db: AsyncSession = Depends(get_db),
    chapter_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Scene]:
    """List all scenes for a specific chapter."""
    return await scene_service.get_by_chapter(db, chapter_id=chapter_id, skip=skip, limit=limit)


@scene_router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(
    *,
    db: AsyncSession = Depends(get_db),
    scene_id: UUID,
) -> Scene:
    """Get a scene by ID."""
    return await scene_service.get(db, id=scene_id)


@scene_router.patch("/{scene_id}", response_model=SceneResponse)
async def update_scene(
    *,
    db: AsyncSession = Depends(get_db),
    scene_id: UUID,
    scene_in: SceneUpdate,
) -> Scene:
    """Update a scene."""
    scene = await scene_service.get(db, id=scene_id)
    return await scene_service.update(db, db_obj=scene, obj_in=scene_in)


@scene_router.delete("/{scene_id}", response_model=SceneResponse)
async def delete_scene(
    *,
    db: AsyncSession = Depends(get_db),
    scene_id: UUID,
) -> Scene:
    """Delete a scene."""
    return await scene_service.delete(db, id=scene_id)
