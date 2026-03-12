"""Health check endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db import engine
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    db_status = "ok"
    redis_status = "ok"

    # Check database connection
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e}"

    # TODO: Check Redis connection
    # redis_status = await check_redis()

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database=db_status,
        redis=redis_status,
    )
