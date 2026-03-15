"""Database initialization utilities."""

import logging

from sqlalchemy import text

from app.db import async_session_maker, engine

logger = logging.getLogger(__name__)


async def create_pgvector_extension() -> None:
    """Create pgvector extension if not exists (PostgreSQL only).

    This function is a no-op for non-PostgreSQL databases like SQLite,
    which are used for testing and local development.
    """
    # Only attempt to create extension for PostgreSQL databases
    dialect = engine.dialect.name
    if dialect == "postgresql":
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.commit()


async def init_database() -> None:
    """Initialize database with required extensions.

    Skips pgvector extension creation for non-PostgreSQL databases.
    """
    await create_pgvector_extension()
    async with async_session_maker() as session:
        try:
            await session.commit()
            logger.info("Initialized database extensions and runtime dependencies")
        except Exception:
            await session.rollback()
            raise


async def reset_database() -> None:
    """Reset database (DEV/TEST ONLY, PostgreSQL only)."""
    dialect = engine.dialect.name
    if dialect != "postgresql":
        raise RuntimeError("reset_database() only supports PostgreSQL")

    async with engine.begin() as conn:
        # Drop all tables (CASCADE)
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.commit()
