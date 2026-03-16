"""Character service layer."""

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException
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

    async def get_by_name(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        name: str,
    ) -> Character | None:
        """Get a character by name within a project."""
        result = await db.execute(
            select(Character).where(
                Character.project_id == project_id,
                Character.name == name,
            )
        )
        return result.scalars().first()

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: CharacterCreate,
        project_id: Any,
    ) -> Character:
        """Create a new character for a specific project.
        
        Raises:
            ConflictException: If a character with the same name already exists.
        """
        existing = await self.get_by_name(db, project_id=project_id, name=obj_in.name)
        if existing:
            raise ConflictException(
                f"Character with name '{obj_in.name}' already exists in this project",
                details={"field": "name", "value": obj_in.name},
            )
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Character(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Character,
        obj_in: CharacterUpdate | dict[str, Any],
    ) -> Character:
        """Update a character.
        
        Raises:
            ConflictException: If updating name to one that already exists.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        if "name" in update_data and update_data["name"] != db_obj.name:
            existing = await self.get_by_name(
                db, project_id=db_obj.project_id, name=update_data["name"]
            )
            if existing:
                raise ConflictException(
                    f"Character with name '{update_data['name']}' already exists in this project",
                    details={"field": "name", "value": update_data["name"]},
                )
        
        return await super().update(db, db_obj=db_obj, obj_in=update_data)


character_service = CRUDCharacter(Character)
