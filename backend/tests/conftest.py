"""Pytest configuration and fixtures."""

import asyncio
import uuid as uuid_lib
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, TypeDecorator, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models import Base

# Test database URL - using SQLite for isolated, dependency-free testing
# Note: For production-like testing with PostgreSQL, override via environment variable
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class SQLiteUUID(TypeDecorator):
    """SQLite-compatible UUID type that stores as string."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Use String for all dialects (simplified for testing)."""
        return String(36)

    def process_bind_param(self, value, dialect):
        """Convert UUID to string for storage."""
        if value is None:
            return None
        if isinstance(value, uuid_lib.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        """Convert string back to UUID."""
        if value is None:
            return None
        if isinstance(value, str):
            return uuid_lib.UUID(value)
        return value


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine() -> AsyncGenerator[Any, None]:
    """Create test database engine with UUID support for SQLite."""

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )

    # Replace UUID columns with SQLite-compatible UUID type
    async def _replace_uuid_types():
        """Replace UUID column types for SQLite compatibility."""
        from sqlalchemy import inspect

        from app.models import Base

        for table in Base.metadata.sorted_tables:
            for col in table.columns:
                if isinstance(col.type, UUID):
                    # Replace with SQLiteUUID
                    col.type = SQLiteUUID()

    await _replace_uuid_types()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with test database dependency override."""
    from app.api.deps import get_db

    # Override the database dependency
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up override
    app.dependency_overrides.clear()
