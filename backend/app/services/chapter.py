"""Chapter, Scene, and Volume service layer."""

from typing import Any

from sqlalchemy import func, select
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
        volume_number = obj_in.volume_number
        if volume_number is None:
            volume_number = await self.next_volume_number(db, project_id=project_id)
        existing = await self.get_by_volume_number(
            db, project_id=project_id, volume_number=volume_number
        )
        if existing:
            raise ConflictException(
                f"Volume with number {volume_number} already exists in this project"
            )
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        obj_dict["volume_number"] = volume_number
        if not str(obj_dict.get("title") or "").strip():
            obj_dict["title"] = f"第{volume_number}卷"
        db_obj = Volume(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Volume,
        obj_in: VolumeUpdate | dict[str, Any],
    ) -> Volume:
        """Update a volume while protecting project-scoped volume numbering."""
        update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else dict(obj_in)
        next_volume_number = update_data.get("volume_number", db_obj.volume_number)
        if next_volume_number is not None and next_volume_number != db_obj.volume_number:
            existing = await self.get_by_volume_number(
                db,
                project_id=db_obj.project_id,
                volume_number=int(next_volume_number),
            )
            if existing and existing.id != db_obj.id:
                raise ConflictException(
                    f"Volume with number {next_volume_number} already exists in this project"
                )
        if "title" in update_data and not str(update_data.get("title") or "").strip():
            update_data["title"] = f"第{next_volume_number or db_obj.volume_number or 1}卷"
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def delete(self, db: AsyncSession, *, id: Any) -> Volume:
        """Delete a volume only when it no longer contains chapters."""
        volume = await self.get(db, id=id)
        chapter_count = (
            await db.execute(
                select(func.count()).select_from(Chapter).where(Chapter.volume_id == volume.id)
            )
        ).scalar_one()
        if chapter_count:
            raise BadRequestException("Cannot delete a volume that still contains chapters")
        return await super().delete(db, id=id)

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

    async def next_volume_number(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
    ) -> int:
        """Return the next available volume number inside a project."""
        result = await db.execute(
            select(func.max(Volume.volume_number)).where(Volume.project_id == project_id)
        )
        return int(result.scalar() or 0) + 1

    async def ensure_default_for_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
    ) -> Volume:
        """Return the first/default volume for a project, creating one if needed."""
        existing = await self.get_by_project(db, project_id=project_id, limit=1)
        if existing:
            return existing[0]
        return await self.create_with_project(
            db,
            obj_in=VolumeCreate(
                project_id=project_id,
                volume_number=1,
                title="第一卷",
                outline="默认兼容卷，用于承接尚未显式编排卷细纲的章节。",
            ),
            project_id=project_id,
        )


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
        effective_volume_id = obj_in.volume_id
        if effective_volume_id is None:
            effective_volume_id = (await volume_service.ensure_default_for_project(db, project_id=project_id)).id
        if not skip_duplicate_check:
            existing = await self.get_by_chapter_number(
                db, project_id=project_id, chapter_number=obj_in.chapter_number, volume_id=effective_volume_id
            )
            if existing:
                raise ConflictException(
                    f"Chapter with number {obj_in.chapter_number} already exists in this project"
                )
        if effective_volume_id:
            volume = await volume_service.get(db, id=effective_volume_id)
            if not volume or volume.project_id != project_id:
                raise BadRequestException(
                    f"Volume {effective_volume_id} does not belong to project {project_id}"
                )
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        obj_dict["volume_id"] = effective_volume_id
        db_obj = Chapter(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Chapter,
        obj_in: ChapterUpdate | dict[str, Any],
    ) -> Chapter:
        """Update a chapter while enforcing volume scope and per-volume numbering."""
        update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else dict(obj_in)
        if "volume_id" in update_data and update_data["volume_id"] is None:
            update_data["volume_id"] = (await volume_service.ensure_default_for_project(db, project_id=db_obj.project_id)).id
        next_volume_id = update_data.get("volume_id", db_obj.volume_id)
        if next_volume_id is None:
            next_volume_id = (await volume_service.ensure_default_for_project(db, project_id=db_obj.project_id)).id
            update_data["volume_id"] = next_volume_id
        if next_volume_id is not None:
            volume = await volume_service.get(db, id=next_volume_id)
            if volume.project_id != db_obj.project_id:
                raise BadRequestException(
                    f"Volume {next_volume_id} does not belong to project {db_obj.project_id}"
                )
        next_chapter_number = int(update_data.get("chapter_number", db_obj.chapter_number))
        existing = await self.get_by_chapter_number(
            db,
            project_id=db_obj.project_id,
            chapter_number=next_chapter_number,
            volume_id=next_volume_id,
        )
        if existing and existing.id != db_obj.id:
            raise ConflictException(
                f"Chapter with number {next_chapter_number} already exists in this volume"
            )
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

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
