"""Suggestion service layer with three-state modification system."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.models.suggestion import Suggestion, SuggestionStatus
from app.schemas.suggestion import SuggestionCreate, SuggestionUpdate
from app.services.base import CRUDBase


class CRUDSuggestion(CRUDBase[Suggestion, SuggestionCreate, SuggestionUpdate]):
    """CRUD operations for Suggestion model with state transitions."""

    async def get_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> list[Suggestion]:
        """Get all suggestions for a project, optionally filtered by status."""
        stmt = select(Suggestion).where(Suggestion.project_id == project_id)
        if status:
            stmt = stmt.where(Suggestion.status == status)
        stmt = stmt.order_by(desc(Suggestion.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_target(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        target_type: str,
        target_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Suggestion]:
        """Get all suggestions for a specific target object within a project."""
        result = await db.execute(
            select(Suggestion)
            .where(
                Suggestion.project_id == project_id,
                Suggestion.target_type == target_type,
                Suggestion.target_id == target_id,
            )
            .order_by(desc(Suggestion.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_count(self, db: AsyncSession, *, project_id: Any) -> int:
        """Count pending (draft/patched) suggestions for a project."""
        from sqlalchemy import func

        result = await db.execute(
            select(func.count())
            .select_from(Suggestion)
            .where(
                Suggestion.project_id == project_id,
                Suggestion.status.in_([SuggestionStatus.DRAFT.value, SuggestionStatus.PATCHED.value]),
            )
        )
        return result.scalar() or 0

    async def confirm(
        self,
        db: AsyncSession,
        *,
        suggestion_id: Any,
        impact_analysis: dict[str, Any] | None = None,
    ) -> Suggestion:
        """Confirm a suggestion (draft -> patched)."""
        suggestion = await self.get(db, id=suggestion_id)
        if suggestion.status != SuggestionStatus.DRAFT.value:
            raise BadRequestException(
                f"Cannot confirm suggestion with status '{suggestion.status}'. "
                f"Only draft suggestions can be confirmed."
            )
        suggestion.status = SuggestionStatus.PATCHED.value
        if impact_analysis is not None:
            suggestion.impact_analysis = impact_analysis
        await db.flush()
        await db.refresh(suggestion)
        return suggestion

    async def discard(self, db: AsyncSession, *, suggestion_id: Any) -> Suggestion:
        """Discard a suggestion (any -> discarded)."""
        suggestion = await self.get(db, id=suggestion_id)
        if suggestion.status == SuggestionStatus.COMMITTED.value:
            raise BadRequestException("Cannot discard a committed suggestion.")
        suggestion.status = SuggestionStatus.DISCARDED.value
        await db.flush()
        await db.refresh(suggestion)
        return suggestion

    async def commit(self, db: AsyncSession, *, suggestion_id: Any) -> Suggestion:
        """Commit a suggestion (patched -> committed).

        Note: This records the commit decision and marks the suggestion as committed.
        The actual content application to the target object will be implemented separately
        as it requires type-specific logic for each target (character, chapter, scene, etc.).
        """
        suggestion = await self.get(db, id=suggestion_id)
        if suggestion.status != SuggestionStatus.PATCHED.value:
            raise BadRequestException(
                f"Cannot commit suggestion with status '{suggestion.status}'. "
                f"Only patched suggestions can be committed."
            )
        suggestion.status = SuggestionStatus.COMMITTED.value
        suggestion.committed_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(suggestion)
        return suggestion

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: SuggestionCreate,
        project_id: Any,
    ) -> Suggestion:
        """Create a new suggestion for a specific project."""
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Suggestion(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


# Singleton instance
suggestion_service = CRUDSuggestion(Suggestion)
