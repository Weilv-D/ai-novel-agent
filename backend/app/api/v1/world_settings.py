"""WorldSetting API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.world_setting import WorldSetting
from app.schemas.world_setting import (
    WorldSettingCreate,
    WorldSettingResponse,
    WorldSettingUpdate,
)
from app.services.world_setting import world_setting_service

router = APIRouter(prefix="/world-settings", tags=["world-settings"])


@router.post("", response_model=WorldSettingResponse, status_code=status.HTTP_201_CREATED)
async def create_world_setting(
    *,
    db: AsyncSession = Depends(get_db),
    setting_in: WorldSettingCreate,
) -> WorldSetting:
    """Create a new world setting."""
    return await world_setting_service.create_with_project(
        db, obj_in=setting_in, project_id=setting_in.project_id
    )


@router.get("/project/{project_id}", response_model=list[WorldSettingResponse])
async def list_world_settings_by_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[WorldSetting]:
    """List all world settings for a specific project."""
    return await world_setting_service.get_by_project(
        db, project_id=project_id, skip=skip, limit=limit
    )


@router.get("/project/{project_id}/category/{category}", response_model=list[WorldSettingResponse])
async def list_world_settings_by_category(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    category: str,
    skip: int = 0,
    limit: int = 100,
) -> list[WorldSetting]:
    """List world settings by category for a project."""
    return await world_setting_service.get_by_category(
        db, project_id=project_id, category=category, skip=skip, limit=limit
    )


@router.get("/{setting_id}", response_model=WorldSettingResponse)
async def get_world_setting(
    *,
    db: AsyncSession = Depends(get_db),
    setting_id: UUID,
) -> WorldSetting:
    """Get a world setting by ID."""
    return await world_setting_service.get(db, id=setting_id)


@router.patch("/{setting_id}", response_model=WorldSettingResponse)
async def update_world_setting(
    *,
    db: AsyncSession = Depends(get_db),
    setting_id: UUID,
    setting_in: WorldSettingUpdate,
) -> WorldSetting:
    """Update a world setting."""
    setting = await world_setting_service.get(db, id=setting_id)
    return await world_setting_service.update(db, db_obj=setting, obj_in=setting_in)


@router.delete("/{setting_id}", response_model=WorldSettingResponse)
async def delete_world_setting(
    *,
    db: AsyncSession = Depends(get_db),
    setting_id: UUID,
) -> WorldSetting:
    """Delete a world setting."""
    return await world_setting_service.delete(db, id=setting_id)
