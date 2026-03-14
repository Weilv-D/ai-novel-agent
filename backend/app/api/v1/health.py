"""Health check endpoints."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns service health status. The API is healthy if it can respond to requests.
    Database and Redis status are reported but do not affect overall health status
    in order to allow the service to run in degraded mode during development.
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        mode="single_user",
        auth_required=bool(settings.admin_api_key),
        api_key_header=settings.api_key_header if settings.admin_api_key else None,
        personal_user_email=settings.personal_user_email,
        database="not_configured",
        redis="not_configured",
    )
