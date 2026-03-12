"""Health check endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns service health status. The API is healthy if it can respond to requests.
    Database and Redis status are reported but do not affect overall health status
    in order to allow the service to run in degraded mode during development.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database="not_configured",
        redis="not_configured",
    )
