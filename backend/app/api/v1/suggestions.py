"""Suggestion API routes for three-state modification system."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.suggestion import Suggestion
from app.schemas.suggestion import (
    SuggestionActionRequest,
    SuggestionActionResult,
    SuggestionCreate,
    SuggestionResponse,
    SuggestionUpdate,
)
from app.services.suggestion import suggestion_service

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.post("", response_model=SuggestionResponse, status_code=status.HTTP_201_CREATED)
async def create_suggestion(
    *,
    db: AsyncSession = Depends(get_db),
    suggestion_in: SuggestionCreate,
) -> Suggestion:
    """Create a new suggestion."""
    return await suggestion_service.create_with_project(
        db, obj_in=suggestion_in, project_id=suggestion_in.project_id
    )


@router.get("", response_model=list[SuggestionResponse])
async def list_suggestions(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> list[Suggestion]:
    """List suggestions for a project, optionally filtered by status."""
    return await suggestion_service.get_by_project(db, project_id=project_id, skip=skip, limit=limit, status=status)


@router.get("/target/{target_type}/{target_id}", response_model=list[SuggestionResponse])
async def list_target_suggestions(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    target_type: str,
    target_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Suggestion]:
    """List suggestions for a specific target object within a project."""
    return await suggestion_service.get_by_target(
        db, project_id=project_id, target_type=target_type, target_id=target_id, skip=skip, limit=limit
    )


@router.get("/pending/count")
async def count_pending_suggestions(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
) -> dict[str, int]:
    """Count pending (draft/patched) suggestions for a project."""
    count = await suggestion_service.get_pending_count(db, project_id=project_id)
    return {"count": count}


@router.get("/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    *,
    db: AsyncSession = Depends(get_db),
    suggestion_id: UUID,
) -> Suggestion:
    """Get a suggestion by ID."""
    return await suggestion_service.get(db, id=suggestion_id)


@router.patch("/{suggestion_id}", response_model=SuggestionResponse)
async def update_suggestion(
    *,
    db: AsyncSession = Depends(get_db),
    suggestion_id: UUID,
    suggestion_in: SuggestionUpdate,
) -> Suggestion:
    """Update a suggestion (content only for draft status)."""
    suggestion = await suggestion_service.get(db, id=suggestion_id)
    return await suggestion_service.update(db, db_obj=suggestion, obj_in=suggestion_in)


@router.post("/{suggestion_id}/action", response_model=SuggestionActionResult)
async def suggestion_action(
    *,
    db: AsyncSession = Depends(get_db),
    suggestion_id: UUID,
    action_req: SuggestionActionRequest,
) -> SuggestionActionResult:
    """Perform an action on a suggestion: confirm, discard, or commit.

    - **confirm**: Move suggestion from draft to patched (with optional impact analysis)
    - **discard**: Discard the suggestion (draft/patched only)
    - **commit**: Mark the suggestion as committed (records intent to apply changes)
    """
    action = action_req.action
    impact_analysis = action_req.impact_analysis

    if action == "confirm":
        await suggestion_service.confirm(db, suggestion_id=suggestion_id, impact_analysis=impact_analysis)
        message = "Suggestion confirmed and awaiting commit"
    elif action == "discard":
        await suggestion_service.discard(db, suggestion_id=suggestion_id)
        message = "Suggestion discarded"
    elif action == "commit":
        await suggestion_service.commit(db, suggestion_id=suggestion_id)
        message = "Suggestion committed (application to target pending)"
    else:
        # This should not happen due to Pydantic validation
        message = f"Unknown action: {action}"

    return SuggestionActionResult(
        success=True, message=message, suggestion_id=suggestion_id, action=action
    )


@router.delete("/{suggestion_id}", response_model=SuggestionResponse)
async def delete_suggestion(
    *,
    db: AsyncSession = Depends(get_db),
    suggestion_id: UUID,
) -> Suggestion:
    """Delete a suggestion."""
    return await suggestion_service.delete(db, id=suggestion_id)
