"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1.characters import router as characters_router
from app.api.v1.chapters import router as chapters_router, scene_router, volume_router
from app.api.v1.dependencies import router as dependencies_router
from app.api.v1.health import router as health_router
from app.api.v1.projects import router as projects_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.suggestions import router as suggestions_router
from app.api.v1.world_settings import router as world_settings_router

router = APIRouter(prefix="/api/v1")

# Include sub-routers
router.include_router(health_router)
router.include_router(projects_router)
router.include_router(characters_router)
router.include_router(world_settings_router)
router.include_router(volume_router)
router.include_router(chapters_router)
router.include_router(scene_router)
router.include_router(suggestions_router)
router.include_router(dependencies_router)
router.include_router(snapshots_router)
