"""Database initialization utilities."""

import logging

from sqlalchemy import text

from app.db import async_session_maker, engine
from app.models import Base

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
    # E2E and local smoke runs use SQLite and do not run Alembic migrations.
    # Create schema from model metadata to avoid missing-table startup failures.
    if engine.dialect.name == "sqlite":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

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
