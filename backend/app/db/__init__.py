"""Database session and connection management."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

# Create engine args based on database type
# SQLite doesn't support pool_size and max_overflow
if settings.database_url.startswith("sqlite"):
    engine_args = {"echo": settings.debug}
else:
    engine_args = {
        "echo": settings.debug,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }

# Create async engine
engine = create_async_engine(settings.database_url, **engine_args)

# Create async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


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


async def init_db() -> None:
    """Initialize database connection."""
    # Test connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


async def close_db() -> None:
    """Close database connection."""
    await engine.dispose()
