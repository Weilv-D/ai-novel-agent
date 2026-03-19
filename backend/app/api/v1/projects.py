"""Project API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectTreeResponse,
    ProjectUpdate,
    ProjectWorkspaceResponse,
)
from app.services.project import project_service
from app.services.project_workspace import project_workspace_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_in: ProjectCreate,
) -> Project:
    """Create a new project."""
    return await project_service.create_project(db, obj_in=project_in)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> list[Project]:
    """List all projects."""
    return await project_service.list_projects(db, skip=skip, limit=limit)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
) -> Project:
    """Get a project by ID."""
    return await project_service.get(db, id=project_id)


@router.get("/{project_id}/tree", response_model=ProjectTreeResponse)
async def get_project_tree(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
) -> ProjectTreeResponse:
    """Get the navigable volume/chapter/scene tree for one project."""
    return await project_workspace_service.get_tree_response(db, project_id=project_id)


@router.get("/{project_id}/workspace", response_model=ProjectWorkspaceResponse)
async def get_project_workspace(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
) -> ProjectWorkspaceResponse:
    """Get the aggregated workspace payload for one project."""
    return await project_workspace_service.get_workspace_response(db, project_id=project_id)


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
