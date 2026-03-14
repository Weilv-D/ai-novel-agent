"""API dependencies."""

from collections.abc import AsyncIterator

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.personal import PersonalUser, get_personal_user
from app.db import async_session_maker


async def get_db() -> AsyncIterator[AsyncSession]:
    """Get database session for dependency injection."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(request: Request) -> PersonalUser:
    """Return the configured single user, optionally enforcing API key access."""
    settings = get_settings()
    expected_api_key = settings.admin_api_key.strip()
    if expected_api_key:
        provided_api_key = request.headers.get(settings.api_key_header)
        if not provided_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing API key in header '{settings.api_key_header}'",
            )
        if provided_api_key != expected_api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )
    return get_personal_user()
