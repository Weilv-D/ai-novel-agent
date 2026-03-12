"""WorldSetting service layer."""

from typing import Any

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world_setting import WorldSetting
from app.schemas.world_setting import WorldSettingCreate, WorldSettingUpdate
from app.services.base import CRUDBase


class CRUDWorldSetting(CRUDBase[WorldSetting, WorldSettingCreate, WorldSettingUpdate]):
    """CRUD operations for WorldSetting model."""

    async def get_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WorldSetting]:
        """Get all world settings for a specific project."""
        result = await db.execute(
            select(WorldSetting)
            .where(WorldSetting.project_id == project_id)
            .order_by(desc(WorldSetting.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_category(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        category: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[WorldSetting]:
        """Get world settings by category for a project."""
        result = await db.execute(
            select(WorldSetting)
            .where(WorldSetting.project_id == project_id)
            .where(WorldSetting.category == category)
            .order_by(desc(WorldSetting.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: WorldSettingCreate,
        project_id: Any,
    ) -> WorldSetting:
        """Create a new world setting for a specific project."""
        obj_dict = obj_in.model_dump()
        db_obj = WorldSetting(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


# Singleton instance
world_setting_service = CRUDWorldSetting(WorldSetting)
