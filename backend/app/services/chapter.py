"""Chapter, Scene, and Volume service layer."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException
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
from app.services.character import character_service


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
        if obj_in.volume_number is not None:
            existing = await self.get_by_volume_number(
                db, project_id=project_id, volume_number=obj_in.volume_number
            )
            if existing:
                raise ConflictException(
                    f"Volume with number {obj_in.volume_number} already exists in this project"
                )
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Volume(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_volume_number(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        volume_number: int | None,
    ) -> Volume | None:
        """Check if a volume with the given number exists in the project."""
        result = await db.execute(
            select(Volume).where(
                Volume.project_id == project_id,
                Volume.volume_number == volume_number,
            )
        )
        return result.scalars().first()


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
        skip_duplicate_check: bool = False,
    ) -> Chapter:
        """Create a new chapter for a specific project."""
        if not skip_duplicate_check:
            existing = await self.get_by_chapter_number(
                db, project_id=project_id, chapter_number=obj_in.chapter_number, volume_id=obj_in.volume_id
            )
            if existing:
                raise ConflictException(
                    f"Chapter with number {obj_in.chapter_number} already exists in this project"
                )
        if obj_in.volume_id:
            volume = await volume_service.get(db, id=obj_in.volume_id)
            if not volume or volume.project_id != project_id:
                raise BadRequestException(
                    f"Volume {obj_in.volume_id} does not belong to project {project_id}"
                )
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Chapter(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_chapter_number(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        chapter_number: int,
        volume_id: Any | None = None,
    ) -> Chapter | None:
        """Check if a chapter with the given number exists in the project."""
        query = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.chapter_number == chapter_number,
        )
        if volume_id is not None:
            query = query.where(Chapter.volume_id == volume_id)
        result = await db.execute(query)
        return result.scalars().first()


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
        skip_duplicate_check: bool = False,
    ) -> Scene:
        """Create a new scene for a specific chapter."""
        chapter = await chapter_service.get(db, id=chapter_id)
        if not chapter:
            raise BadRequestException(f"Chapter {chapter_id} does not exist")
        if obj_in.pov_character_id:
            character = await character_service.get(db, id=obj_in.pov_character_id)
            if not character or character.project_id != chapter.project_id:
                raise BadRequestException(
                    f"Character {obj_in.pov_character_id} does not belong to the same project as the chapter"
                )
        if not skip_duplicate_check:
            existing = await self.get_by_scene_order(
                db, chapter_id=chapter_id, scene_order=obj_in.scene_order
            )
            if existing:
                raise ConflictException(
                    f"Scene with order {obj_in.scene_order} already exists in this chapter"
                )
        obj_dict = obj_in.model_dump(exclude={"chapter_id"})
        db_obj = Scene(**obj_dict, chapter_id=chapter_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_scene_order(
        self,
        db: AsyncSession,
        *,
        chapter_id: Any,
        scene_order: int,
    ) -> Scene | None:
        """Check if a scene with the given order exists in the chapter."""
        result = await db.execute(
            select(Scene).where(
                Scene.chapter_id == chapter_id,
                Scene.scene_order == scene_order,
            )
        )
        return result.scalars().first()


# Singleton instances
volume_service = CRUDVolume(Volume)
chapter_service = CRUDChapter(Chapter)
scene_service = CRUDScene(Scene)
