"""Database initialization utilities."""

from sqlalchemy import text

from app.db import engine


async def create_pgvector_extension() -> None:
    """Create pgvector extension if not exists."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.commit()


async def init_database() -> None:
    """Initialize database with required extensions."""
    await create_pgvector_extension()


async def reset_database() -> None:
    """Reset database (DEV/TEST ONLY)."""
    async with engine.begin() as conn:
        # Drop all tables (CASCADE)
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.commit()
