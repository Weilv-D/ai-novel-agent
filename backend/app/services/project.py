"""Project service layer."""

from typing import Any, cast

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import DEFAULT_AGENT_PROFILE_ID, Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base import CRUDBase


def build_initial_story_outline(
    *,
    summary: str | None = None,
    notes: str | None = None,
    story_outline: str | None = None,
) -> str | None:
    """Build a canonical initial project outline from legacy free-text fields."""
    explicit_outline = (story_outline or "").strip()
    if explicit_outline:
        return explicit_outline

    summary_text = (summary or "").strip()
    notes_text = (notes or "").strip()
    if not summary_text and not notes_text:
        return None
    if summary_text and notes_text:
        return f"【项目简介】\n{summary_text}\n\n【补充备注】\n{notes_text}"
    return summary_text or notes_text


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
        obj_dict["story_outline"] = build_initial_story_outline(
            summary=cast(str | None, obj_dict.get("summary")),
            notes=cast(str | None, obj_dict.get("notes")),
            story_outline=cast(str | None, obj_dict.get("story_outline")),
        )
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
        if "story_outline" in update_data:
            update_data["story_outline"] = build_initial_story_outline(
                story_outline=cast(str | None, update_data.get("story_outline")),
                summary=cast(str | None, update_data.get("summary", db_obj.summary)),
                notes=cast(str | None, update_data.get("notes", db_obj.notes)),
            )
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
