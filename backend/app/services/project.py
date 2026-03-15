"""Project service layer."""

from typing import Any, cast

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import DEFAULT_AGENT_PROFILE_ID, Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base import CRUDBase


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """CRUD operations for Project model."""

    async def list_projects(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        """Get all projects ordered by most recently updated."""
        result = await db.execute(
            select(Project)
            .order_by(desc(Project.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_project(
        self,
        db: AsyncSession,
        *,
        obj_in: ProjectCreate,
    ) -> Project:
        """Create a new project."""
        obj_dict = obj_in.model_dump()
        profile_id = str(obj_dict.pop("agent_profile_id", DEFAULT_AGENT_PROFILE_ID))
        meta = dict(obj_dict.pop("meta", {}) or {})
        meta.setdefault("agent_profile_id", profile_id)
        db_obj = Project(**obj_dict, meta=meta)
        db_obj.agent_profile_id = profile_id
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Project,
        obj_in: ProjectUpdate | dict[str, Any],
    ) -> Project:
        """Update a project while preserving profile metadata semantics."""
        if hasattr(obj_in, "model_dump"):
            update_data = cast(dict[str, Any], obj_in.model_dump(exclude_unset=True))
        else:
            update_data = dict(obj_in)

        next_profile_id = cast(str | None, update_data.pop("agent_profile_id", None))
        if "meta" in update_data:
            next_meta = dict(update_data.pop("meta") or {})
            next_meta.setdefault("agent_profile_id", db_obj.agent_profile_id)
            db_obj.meta = next_meta

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        if next_profile_id is not None:
            db_obj.agent_profile_id = next_profile_id

        await db.flush()
        await db.refresh(db_obj)
        return db_obj


# Singleton instance
project_service = CRUDProject(Project)
