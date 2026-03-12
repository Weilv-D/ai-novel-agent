"""Snapshot schemas for version control and rollback."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ============ Enums ============

# Type literals for snapshot targets
SnapshotTargetTypeLiteral = Literal[
    "project", "character", "world_setting", "volume", "chapter", "scene", "suggestion"
]


# ============ Snapshot Schemas ============


class SnapshotBase(BaseModel):
    """Base snapshot schema."""

    target_type: SnapshotTargetTypeLiteral = Field(
        ..., description="Type of the target object"
    )
    target_id: UUID = Field(..., description="ID of the target object")
    data: dict[str, Any] = Field(..., description="JSON representation of the object state")


class SnapshotCreate(SnapshotBase):
    """Schema for creating a snapshot."""

    project_id: UUID = Field(..., description="Project ID this snapshot belongs to")


class SnapshotUpdate(BaseModel):
    """Schema for updating a snapshot.

    Note: Only data can be updated via PATCH (for corrections).
    """

    data: dict[str, Any] | None = None


class SnapshotResponse(SnapshotBase):
    """Schema for snapshot response."""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============ Query Schemas ============


class SnapshotQueryRequest(BaseModel):
    """Schema for querying snapshots."""

    target_type: SnapshotTargetTypeLiteral | None = None
    target_id: UUID | None = None


# ============ Rollback Schemas ============


class RollbackRequest(BaseModel):
    """Schema for rolling back to a snapshot."""

    snapshot_id: UUID = Field(..., description="ID of the snapshot to rollback to")


class RollbackResponse(BaseModel):
    """Schema for rollback response."""

    snapshot_id: UUID
    target_type: SnapshotTargetTypeLiteral
    target_id: UUID
    rolled_back_at: datetime
    message: str = Field(
        ..., description="Confirmation message about the rollback operation"
    )
