"""Pytest configuration and fixtures."""

import asyncio
import os
import tempfile
import uuid as uuid_lib
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from pathlib import Path
from typing import Any

import fastapi.testclient
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import String, TypeDecorator, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker

# Isolate tests from any developer-local backend/.env values.
TEST_ENV_DEFAULTS = {
    "DEBUG": "true",
    "CORS_ORIGINS": "http://localhost:3000,http://localhost:3001",
    "LLM_API_KEY": "",
    "LLM_BASE_URL": "https://api.openai.com/v1",
    "LLM_MODEL": "gpt-4o-mini",
    "MAX_TOKENS": "4096",
    "TEMPERATURE": "0.7",
    "EMBEDDING_API_KEY": "",
    "EMBEDDING_BASE_URL": "",
    "EMBEDDING_MODEL": "text-embedding-3-small",
    "EMBEDDING_DIMENSION": "1536",
}
for key, value in TEST_ENV_DEFAULTS.items():
    os.environ[key] = value

from app.main import app
from app.models import Base


# Test database URL - using SQLite for isolated, dependency-free testing
# Note: For production-like testing with PostgreSQL, override via environment variable
class CompatibleTestClient:
    """Minimal sync test client backed by httpx ASGI transport.

    Starlette's TestClient currently hangs in this environment when issuing
    requests from synchronous tests. This wrapper preserves the simple
    request/response API used by the test suite.
    """

    __test__ = False

    def __init__(
        self,
        app: Any,
        *,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        headers: dict[str, str] | None = None,
        follow_redirects: bool = True,
        **_: Any,
    ) -> None:
        self.app = app
        self.base_url = base_url
        self.raise_server_exceptions = raise_server_exceptions
        self.headers = headers or {}
        self.follow_redirects = follow_redirects

    async def _request_async(self, method: str, url: str, **kwargs: Any) -> Response:
        transport = ASGITransport(
            app=self.app,
            raise_app_exceptions=self.raise_server_exceptions,
        )
        async with AsyncClient(
            transport=transport,
            base_url=self.base_url,
            headers=self.headers,
            follow_redirects=self.follow_redirects,
        ) as client:
            return await client.request(method, url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        return asyncio.run(self._request_async(method, url, **kwargs))

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        return self.request("PATCH", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        return self.request("DELETE", url, **kwargs)

    def __enter__(self) -> "CompatibleTestClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


fastapi.testclient.TestClient = CompatibleTestClient


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


class AsyncCompatibleConnection:
    """Async-shaped wrapper around a synchronous SQLAlchemy connection."""

    def __init__(self, connection: Any):
        self._connection = connection

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self._connection.execute(*args, **kwargs)


class AsyncCompatibleBeginContext:
    """Async context manager proxy for engine.begin()."""

    def __init__(self, begin_ctx: Any):
        self._begin_ctx = begin_ctx
        self._connection: Any | None = None

    async def __aenter__(self) -> AsyncCompatibleConnection:
        self._connection = self._begin_ctx.__enter__()
        return AsyncCompatibleConnection(self._connection)

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._begin_ctx.__exit__(exc_type, exc, tb)


class AsyncCompatibleEngine:
    """Async-shaped wrapper around a synchronous SQLAlchemy engine."""

    def __init__(self, engine: Any):
        self._engine = engine

    def begin(self) -> AsyncCompatibleBeginContext:
        return AsyncCompatibleBeginContext(self._engine.begin())

    async def dispose(self) -> None:
        self._engine.dispose()


class AsyncCompatibleSession:
    """Async-shaped wrapper around a synchronous SQLAlchemy session."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, instance: Any) -> None:
        self._session.add(instance)

    def add_all(self, instances: list[Any]) -> None:
        self._session.add_all(instances)

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self._session.execute(*args, **kwargs)

    async def flush(self) -> None:
        self._session.flush()

    async def refresh(self, instance: Any) -> None:
        self._session.refresh(instance)

    async def delete(self, instance: Any) -> None:
        self._session.delete(instance)

    async def commit(self) -> None:
        self._session.commit()

    async def rollback(self) -> None:
        self._session.rollback()

    async def close(self) -> None:
        self._session.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_engine() -> Generator[Any, None, None]:
    """Create test database engine with UUID support for SQLite."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)

    sync_engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
    )
    wrapped_engine = AsyncCompatibleEngine(sync_engine)

    # Replace UUID columns with SQLite-compatible UUID type
    def _replace_uuid_types() -> None:
        """Replace UUID column types for SQLite compatibility."""
        for table in Base.metadata.sorted_tables:
            for col in table.columns:
                if isinstance(col.type, UUID):
                    col.type = SQLiteUUID()

    # Save original UUID column types to restore after test
    _original_types = {}
    for table in Base.metadata.sorted_tables:
        for col in table.columns:
            if isinstance(col.type, UUID):
                _original_types[(table.name, col.name)] = col.type

    _replace_uuid_types()

    # Create all tables
    with sync_engine.begin() as conn:
        Base.metadata.create_all(bind=conn)

    yield wrapped_engine

    sync_engine.dispose()
    if db_path.exists():
        db_path.unlink()

    # Restore original UUID column types to prevent global side effects
    for table in Base.metadata.sorted_tables:
        for col in table.columns:
            if (table.name, col.name) in _original_types:
                col.type = _original_types[(table.name, col.name)]


@pytest.fixture(scope="function")
def db_session(db_engine: Any) -> Generator[AsyncSession, None, None]:
    """Create test database session."""
    sync_session_maker = sessionmaker(
        bind=db_engine._engine,
        class_=Session,
        expire_on_commit=False,
    )

    raw_session = sync_session_maker()
    session = AsyncCompatibleSession(raw_session)
    try:
        yield session
    finally:
        session._session.close()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with test database dependency override."""
    from app.api.deps import get_db

    # Override the database dependency
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up override
    app.dependency_overrides.clear()
