"""Snapshot API routes for version control and rollback."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.snapshot import Snapshot
from app.schemas.snapshot import (
    RollbackRequest,
    RollbackResponse,
    SnapshotCreate,
    SnapshotResponse,
    SnapshotTargetTypeLiteral,
    SnapshotUpdate,
)
from app.services.snapshot import snapshot_service

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.post("", response_model=SnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    *,
    db: AsyncSession = Depends(get_db),
    snapshot_in: SnapshotCreate,
) -> Snapshot:
    """Create a new snapshot for version control."""
    return await snapshot_service.create_with_project(
        db, obj_in=snapshot_in, project_id=snapshot_in.project_id
    )


@router.get("", response_model=list[SnapshotResponse])
async def list_snapshots(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Snapshot]:
    """List all snapshots for a project."""
    return await snapshot_service.get_by_project(
        db, project_id=project_id, skip=skip, limit=limit
    )


@router.get("/target/{target_type}/{target_id}", response_model=list[SnapshotResponse])
async def list_target_snapshots(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    target_type: str,
    target_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Snapshot]:
    """List all snapshots for a specific target object."""
    return await snapshot_service.get_by_target(
        db,
        project_id=project_id,
        target_type=target_type,
        target_id=target_id,
        skip=skip,
        limit=limit,
    )


@router.get("/target/{target_type}/{target_id}/latest", response_model=SnapshotResponse)
async def get_latest_snapshot(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    target_type: str,
    target_id: UUID,
) -> Snapshot:
    """Get the latest snapshot for a specific target object."""
    snapshot = await snapshot_service.get_latest_by_target(
        db, project_id=project_id, target_type=target_type, target_id=target_id
    )
    if not snapshot:
        from app.core.exceptions import NotFoundException

        raise NotFoundException(
            f"No snapshot found for {target_type}:{target_id} in project {project_id}"
        )
    return snapshot


@router.get("/count", response_model=dict[str, Any])
async def count_snapshots(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    target_type: str | None = None,
) -> dict[str, Any]:
    """Count snapshots for a project, optionally filtered by target type."""
    count = await snapshot_service.count_by_project(db, project_id=project_id, target_type=target_type)
    return {"count": count, "project_id": str(project_id), "target_type": target_type}


@router.post("/rollback", response_model=RollbackResponse)
async def rollback_to_snapshot(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request: RollbackRequest,
) -> RollbackResponse:
    """Rollback a target object to a specific snapshot.

    Note: This endpoint returns the snapshot data for rollback.
    The actual application of the rollback data to the target object
    should be handled by the client or a separate service that knows
    how to update each target type.

    Returns the snapshot data that can be used to restore the object state.
    """
    snapshot = await snapshot_service.get(db, id=request.snapshot_id)

    # Verify the snapshot belongs to the project
    if snapshot.project_id != project_id:
        from app.core.exceptions import BadRequestException

        raise BadRequestException(
            f"Snapshot {request.snapshot_id} does not belong to project {project_id}"
        )

    return RollbackResponse(
        snapshot_id=snapshot.id,
        target_type=snapshot.target_type,  # type: ignore[arg-type]
        target_id=snapshot.target_id,
        rolled_back_at=datetime.now(UTC),
        message=f"Rollback data prepared for {snapshot.target_type}:{snapshot.target_id}. "
        f"Apply the snapshot.data to restore the object state.",
    )


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(
    *,
    db: AsyncSession = Depends(get_db),
    snapshot_id: UUID,
) -> Snapshot:
    """Get a snapshot by ID."""
    return await snapshot_service.get(db, id=snapshot_id)


@router.get("/{snapshot_id}/data", response_model=dict[str, Any])
async def get_snapshot_data(
    *,
    db: AsyncSession = Depends(get_db),
    snapshot_id: UUID,
) -> dict[str, Any]:
    """Get the data stored in a snapshot (for rollback operations)."""
    data = await snapshot_service.get_snapshot_data(db, snapshot_id=snapshot_id)
    if data is None:
        from app.core.exceptions import NotFoundException

        raise NotFoundException(f"Snapshot {snapshot_id} not found")
    return data


@router.patch("/{snapshot_id}", response_model=SnapshotResponse)
async def update_snapshot(
    *,
    db: AsyncSession = Depends(get_db),
    snapshot_id: UUID,
    snapshot_in: SnapshotUpdate,
) -> Snapshot:
    """Update a snapshot (only data can be updated for corrections)."""
    snapshot = await snapshot_service.get(db, id=snapshot_id)
    return await snapshot_service.update(db, db_obj=snapshot, obj_in=snapshot_in)


@router.delete("/{snapshot_id}", response_model=SnapshotResponse)
async def delete_snapshot(
    *,
    db: AsyncSession = Depends(get_db),
    snapshot_id: UUID,
) -> Snapshot:
    """Delete a snapshot by ID."""
    return await snapshot_service.delete(db, id=snapshot_id)
