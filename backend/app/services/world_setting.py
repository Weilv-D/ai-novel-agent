"""WorldSetting service layer."""

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException
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

    async def get_by_name(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        name: str,
        category: str | None = None,
    ) -> WorldSetting | None:
        """Get a world setting by name within a project.

        Args:
            db: Database session
            project_id: Project UUID
            name: World setting name
            category: Optional category filter for category-scoped uniqueness
        """
        query = select(WorldSetting).where(
            WorldSetting.project_id == project_id,
            WorldSetting.name == name,
        )
        if category is not None:
            query = query.where(WorldSetting.category == category)
        result = await db.execute(query)
        return result.scalars().first()

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: WorldSettingCreate,
        project_id: Any,
    ) -> WorldSetting:
        """Create a new world setting for a specific project.

        Raises:
            BadRequestException: If content is explicitly set to an empty string.
            ConflictException: If a world setting with the same name already exists in the same category.
        """
        if obj_in.content is not None and not obj_in.content.strip():
            raise BadRequestException(
                "World setting content cannot be empty",
                details={"field": "content"},
            )

        existing = await self.get_by_name(
            db, project_id=project_id, name=obj_in.name, category=obj_in.category
        )
        if existing:
            raise ConflictException(
                f"World setting with name '{obj_in.name}' already exists in category '{obj_in.category}'",
                details={"field": "name", "value": obj_in.name, "category": obj_in.category},
            )

        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = WorldSetting(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: WorldSetting,
        obj_in: WorldSettingUpdate | dict[str, Any],
    ) -> WorldSetting:
        """Update a world setting.

        Raises:
            BadRequestException: If content is being set to empty.
            ConflictException: If updating name to one that already exists in the same category.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "content" in update_data:
            if update_data["content"] is not None and not update_data["content"].strip():
                raise BadRequestException(
                    "World setting content cannot be empty",
                    details={"field": "content"},
                )

        name_changed = "name" in update_data and update_data["name"] != db_obj.name
        category_changed = "category" in update_data and update_data["category"] != db_obj.category

        if name_changed or category_changed:
            new_name = update_data.get("name", db_obj.name)
            new_category = update_data.get("category", db_obj.category)
            existing = await self.get_by_name(
                db, project_id=db_obj.project_id, name=new_name, category=new_category
            )
            if existing and existing.id != db_obj.id:
                raise ConflictException(
                    f"World setting with name '{new_name}' already exists in category '{new_category}'",
                    details={"field": "name", "value": new_name, "category": new_category},
                )

        return await super().update(db, db_obj=db_obj, obj_in=update_data)


world_setting_service = CRUDWorldSetting(WorldSetting)
