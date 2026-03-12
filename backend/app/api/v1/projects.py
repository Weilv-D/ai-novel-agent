"""Project API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_in: ProjectCreate,
    # TODO: Add current_user dependency
    # current_user: User = Depends(get_current_user),
) -> Project:
    """Create a new project."""
    # TODO: Replace with actual user_id from current_user
    user_id = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder
    return await project_service.create_with_user(db, obj_in=project_in, user_id=user_id)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    # TODO: Add current_user dependency
) -> list[Project]:
    """List all projects for the current user."""
    # TODO: Replace with actual user_id from current_user
    user_id = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder
    return await project_service.get_by_user(db, user_id=user_id, skip=skip, limit=limit)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
) -> Project:
    """Get a project by ID."""
    return await project_service.get(db, id=project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    project_in: ProjectUpdate,
) -> Project:
    """Update a project."""
    project = await project_service.get(db, id=project_id)
    return await project_service.update(db, db_obj=project, obj_in=project_in)


@router.delete("/{project_id}", response_model=ProjectResponse)
async def delete_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
) -> Project:
    """Delete a project."""
    return await project_service.delete(db, id=project_id)
