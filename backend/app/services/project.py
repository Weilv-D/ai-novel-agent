"""Project service layer."""

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base import CRUDBase


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """CRUD operations for Project model."""

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        """Get all projects for a specific user."""
        result = await db.execute(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(desc(Project.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_with_user(
        self,
        db: AsyncSession,
        *,
        obj_in: ProjectCreate,
        user_id: Any,
    ) -> Project:
        """Create a new project for a specific user."""
        obj_dict = obj_in.model_dump()
        db_obj = Project(**obj_dict, user_id=user_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


# Singleton instance
project_service = CRUDProject(Project)
