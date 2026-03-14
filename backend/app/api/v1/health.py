"""Health check endpoints."""

import inspect

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db import engine
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


async def get_database_status() -> str:
    """Return database connectivity status."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unavailable"


async def get_redis_status(redis_url: str) -> str:
    """Return Redis connectivity status."""
    if not redis_url:
        return "not_configured"

    client = Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
    try:
        ping_result = client.ping()
        if inspect.isawaitable(ping_result):
            await ping_result
        return "healthy"
    except Exception:
        return "unavailable"
    finally:
        close_result = client.aclose()
        if inspect.isawaitable(close_result):
            await close_result


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns service health status. The API is healthy if it can respond to requests.
    Database and Redis status are reported but do not affect overall health status
    in order to allow the service to run in degraded mode during development.
    """
    settings = get_settings()
    database_status = await get_database_status()
    redis_status = await get_redis_status(settings.redis_url)

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        mode="single_user",
        auth_required=bool(settings.admin_api_key),
        api_key_header=settings.api_key_header if settings.admin_api_key else None,
        personal_user_email=settings.personal_user_email,
        database=database_status,
        redis=redis_status,
    )
