"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router

router = APIRouter(prefix="/api/v1")

# Include sub-routers
router.include_router(health_router)
