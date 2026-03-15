"""Dependency API routes for impact analysis and relationship tracking."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.dependency import Dependency
from app.schemas.dependency import (
    DependencyCreate,
    DependencyEntityTypeLiteral,
    DependencyResponse,
    DependencyUpdate,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
)
from app.services.dependency import dependency_service

router = APIRouter(prefix="/dependencies", tags=["dependencies"])


@router.post("", response_model=DependencyResponse, status_code=status.HTTP_201_CREATED)
async def create_dependency(
    *,
    db: AsyncSession = Depends(get_db),
    dependency_in: DependencyCreate,
) -> Dependency:
    """Create a new dependency relationship."""
    return await dependency_service.create_with_project(
        db, obj_in=dependency_in, project_id=dependency_in.project_id
    )


@router.get("", response_model=list[DependencyResponse])
async def query_dependencies(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    source_type: str | None = None,
    source_id: UUID | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    dependency_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Dependency]:
    """Query dependencies with optional filters."""
    return await dependency_service.query_dependencies(
        db,
        project_id=project_id,
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        dependency_type=dependency_type,
        skip=skip,
        limit=limit,
    )


@router.get("/source/{source_type}/{source_id}", response_model=list[DependencyResponse])
async def list_source_dependencies(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    source_type: str,
    source_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Dependency]:
    """List all dependencies from a specific source object."""
    return await dependency_service.get_by_source(
        db, project_id=project_id, source_type=source_type, source_id=source_id, skip=skip, limit=limit
    )


@router.get("/target/{target_type}/{target_id}", response_model=list[DependencyResponse])
async def list_target_dependencies(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    target_type: str,
    target_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Dependency]:
    """List all dependencies pointing to a specific target object."""
    return await dependency_service.get_by_target(
        db, project_id=project_id, target_type=target_type, target_id=target_id, skip=skip, limit=limit
    )


@router.post("/analyze", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request: ImpactAnalysisRequest,
) -> ImpactAnalysisResponse:
    """Analyze the impact of modifying a source object.

    Returns all objects that would be affected by modifying the specified source object.
    """
    impacts = await dependency_service.analyze_impact(
        db,
        project_id=project_id,
        source_type=request.source_type,
        source_id=request.source_id,
    )

    return ImpactAnalysisResponse(
        source_type=request.source_type,
        source_id=request.source_id,
        impacted_objects=impacts,
        total_count=len(impacts),
        analysis_summary=f"Modifying {request.source_type}:{request.source_id} affects {len(impacts)} object(s)",
    )


@router.post("/analyze/reverse/{target_type}/{target_id}", response_model=ImpactAnalysisResponse)
async def analyze_reverse_impact(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    target_type: str,
    target_id: UUID,
) -> ImpactAnalysisResponse:
    """Analyze what would be affected if a target object is modified.

    Returns all source objects that depend on this target.
    """
    impacts = await dependency_service.analyze_reverse_impact(
        db,
        project_id=project_id,
        target_type=target_type,
        target_id=target_id,
    )

    return ImpactAnalysisResponse(
        source_type=target_type,  # type: ignore[arg-type]
        source_id=target_id,
        impacted_objects=impacts,
        total_count=len(impacts),
        analysis_summary=f"{len(impacts)} object(s) depend on {target_type}:{target_id}",
    )


@router.get("/{dependency_id}", response_model=DependencyResponse)
async def get_dependency(
    *,
    db: AsyncSession = Depends(get_db),
    dependency_id: UUID,
) -> Dependency:
    """Get a dependency by ID."""
    return await dependency_service.get(db, id=dependency_id)


@router.patch("/{dependency_id}", response_model=DependencyResponse)
async def update_dependency(
    *,
    db: AsyncSession = Depends(get_db),
    dependency_id: UUID,
    dependency_in: DependencyUpdate,
) -> Dependency:
    """Update a dependency (only dependency_type can be updated)."""
    dependency = await dependency_service.get(db, id=dependency_id)
    return await dependency_service.update(db, db_obj=dependency, obj_in=dependency_in)


@router.delete("/{dependency_id}", response_model=DependencyResponse)
async def delete_dependency(
    *,
    db: AsyncSession = Depends(get_db),
    dependency_id: UUID,
) -> Dependency:
    """Delete a dependency by ID."""
    return await dependency_service.delete(db, id=dependency_id)
