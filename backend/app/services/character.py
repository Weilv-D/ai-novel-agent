"""Character service layer."""

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.schemas.character import CharacterCreate, CharacterUpdate
from app.services.base import CRUDBase


class CRUDCharacter(CRUDBase[Character, CharacterCreate, CharacterUpdate]):
    """CRUD operations for Character model."""

    async def get_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Character]:
        """Get all characters for a specific project."""
        result = await db.execute(
            select(Character)
            .where(Character.project_id == project_id)
            .order_by(desc(Character.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: CharacterCreate,
        project_id: Any,
    ) -> Character:
        """Create a new character for a specific project."""
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Character(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


# Singleton instance
character_service = CRUDCharacter(Character)
