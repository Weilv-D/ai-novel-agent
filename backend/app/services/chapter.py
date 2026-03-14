"""Chapter, Scene, and Volume service layer."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter, Scene, Volume
from app.schemas.chapter import (
    ChapterCreate,
    ChapterUpdate,
    SceneCreate,
    SceneUpdate,
    VolumeCreate,
    VolumeUpdate,
)
from app.services.base import CRUDBase


class CRUDVolume(CRUDBase[Volume, VolumeCreate, VolumeUpdate]):
    """CRUD operations for Volume model."""

    async def get_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Volume]:
        """Get all volumes for a specific project."""
        result = await db.execute(
            select(Volume)
            .where(Volume.project_id == project_id)
            .order_by(Volume.volume_number.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: VolumeCreate,
        project_id: Any,
    ) -> Volume:
        """Create a new volume for a specific project."""
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Volume(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


class CRUDChapter(CRUDBase[Chapter, ChapterCreate, ChapterUpdate]):
    """CRUD operations for Chapter model."""

    async def get_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Chapter]:
        """Get all chapters for a specific project."""
        result = await db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_number.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_volume(
        self,
        db: AsyncSession,
        *,
        volume_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Chapter]:
        """Get all chapters for a specific volume."""
        result = await db.execute(
            select(Chapter)
            .where(Chapter.volume_id == volume_id)
            .order_by(Chapter.chapter_number.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: ChapterCreate,
        project_id: Any,
    ) -> Chapter:
        """Create a new chapter for a specific project."""
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Chapter(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


class CRUDScene(CRUDBase[Scene, SceneCreate, SceneUpdate]):
    """CRUD operations for Scene model."""

    async def get_by_chapter(
        self,
        db: AsyncSession,
        *,
        chapter_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Scene]:
        """Get all scenes for a specific chapter."""
        result = await db.execute(
            select(Scene)
            .where(Scene.chapter_id == chapter_id)
            .order_by(Scene.scene_order.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_with_chapter(
        self,
        db: AsyncSession,
        *,
        obj_in: SceneCreate,
        chapter_id: Any,
    ) -> Scene:
        """Create a new scene for a specific chapter."""
        obj_dict = obj_in.model_dump(exclude={"chapter_id"})
        db_obj = Scene(**obj_dict, chapter_id=chapter_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


# Singleton instances
volume_service = CRUDVolume(Volume)
chapter_service = CRUDChapter(Chapter)
scene_service = CRUDScene(Scene)
