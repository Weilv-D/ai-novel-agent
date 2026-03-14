"""Snapshot service layer for version control and rollback."""

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import Snapshot
from app.schemas.snapshot import SnapshotCreate, SnapshotUpdate
from app.services.base import CRUDBase


class CRUDSnapshot(CRUDBase[Snapshot, SnapshotCreate, SnapshotUpdate]):
    """CRUD operations for Snapshot model with version control features."""

    async def get_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Snapshot]:
        """Get all snapshots for a project."""
        stmt = (
            select(Snapshot)
            .where(Snapshot.project_id == project_id)
            .order_by(desc(Snapshot.created_at))
            .offset(skip)
            .limit(limit)
        )
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
    ) -> list[Snapshot]:
        """Get all snapshots for a specific target object within a project."""
        result = await db.execute(
            select(Snapshot)
            .where(
                Snapshot.project_id == project_id,
                Snapshot.target_type == target_type,
                Snapshot.target_id == target_id,
            )
            .order_by(desc(Snapshot.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_by_target(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        target_type: str,
        target_id: Any,
    ) -> Snapshot | None:
        """Get the latest snapshot for a specific target object."""
        result = await db.execute(
            select(Snapshot)
            .where(
                Snapshot.project_id == project_id,
                Snapshot.target_type == target_type,
                Snapshot.target_id == target_id,
            )
            .order_by(desc(Snapshot.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_snapshot(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        target_type: str,
        target_id: Any,
        data: dict[str, Any],
    ) -> Snapshot:
        """Create a snapshot for a target object."""
        snapshot = Snapshot(
            project_id=project_id, target_type=target_type, target_id=target_id, data=data
        )
        db.add(snapshot)
        await db.flush()
        await db.refresh(snapshot)
        return snapshot

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: SnapshotCreate,
        project_id: Any,
    ) -> Snapshot:
        """Create a new snapshot for a specific project."""
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Snapshot(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_snapshot_data(
        self, db: AsyncSession, *, snapshot_id: Any
    ) -> dict[str, Any] | None:
        """Get the data stored in a snapshot."""
        from app.core.exceptions import NotFoundException

        try:
            snapshot = await self.get(db, id=snapshot_id)
            return snapshot.data if snapshot else None
        except NotFoundException:
            return None

    async def count_by_project(
        self, db: AsyncSession, *, project_id: Any, target_type: str | None = None
    ) -> int:
        """Count snapshots for a project, optionally filtered by target type."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Snapshot).where(Snapshot.project_id == project_id)
        if target_type:
            stmt = stmt.where(Snapshot.target_type == target_type)
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def count_by_target(
        self, db: AsyncSession, *, project_id: Any, target_type: str, target_id: Any
    ) -> int:
        """Count snapshots for a specific target object."""
        from sqlalchemy import func

        result = await db.execute(
            select(func.count())
            .select_from(Snapshot)
            .where(
                Snapshot.project_id == project_id,
                Snapshot.target_type == target_type,
                Snapshot.target_id == target_id,
            )
        )
        return result.scalar() or 0


# Singleton instance
snapshot_service = CRUDSnapshot(Snapshot)
