"""Project API routes."""

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
