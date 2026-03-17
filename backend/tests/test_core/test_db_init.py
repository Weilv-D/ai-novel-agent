"""Tests for database initialization helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.db import init_db as db_init_module


class FakeConnection:
    """Async-shaped connection stub for init-db tests."""

    def __init__(self) -> None:
        self.execute = AsyncMock()
        self.commit = AsyncMock()
        self.run_sync = AsyncMock()


class FakeBeginContext:
    """Async context manager wrapping a fake connection."""

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeEngine:
    """Engine stub exposing the pieces init_db.py uses."""

    def __init__(self, dialect_name: str, connection: FakeConnection) -> None:
        self.dialect = SimpleNamespace(name=dialect_name)
        self._connection = connection
        self.begin_calls = 0

    def begin(self) -> FakeBeginContext:
        self.begin_calls += 1
        return FakeBeginContext(self._connection)


class FakeSessionContext:
    """Async context manager for the mocked session factory."""

    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class TestInitDbHelpers:
    """Covers database bootstrap helpers for SQLite and PostgreSQL paths."""

    @pytest.mark.asyncio
    async def test_create_pgvector_extension_skips_non_postgres(self) -> None:
        """Non-PostgreSQL engines should not attempt extension creation."""
        connection = FakeConnection()
        engine = FakeEngine("sqlite", connection)

        with patch.object(db_init_module, "engine", engine):
            await db_init_module.create_pgvector_extension()

        assert engine.begin_calls == 0
        connection.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_pgvector_extension_executes_on_postgres(self) -> None:
        """PostgreSQL engines should create the pgvector extension."""
        connection = FakeConnection()
        engine = FakeEngine("postgresql", connection)

        with patch.object(db_init_module, "engine", engine):
            await db_init_module.create_pgvector_extension()

        assert engine.begin_calls == 1
        connection.execute.assert_awaited_once()
        assert "CREATE EXTENSION IF NOT EXISTS vector" in str(connection.execute.await_args.args[0])
        connection.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_database_for_sqlite_creates_schema_and_commits(self) -> None:
        """SQLite startup should create metadata tables and commit the session."""
        connection = FakeConnection()
        engine = FakeEngine("sqlite", connection)
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())

        with patch.object(db_init_module, "engine", engine):
            with patch.object(db_init_module, "create_pgvector_extension", new_callable=AsyncMock) as mock_ext:
                with patch.object(db_init_module, "async_session_maker", return_value=FakeSessionContext(session)):
                    await db_init_module.init_database()

        connection.run_sync.assert_awaited_once()
        assert connection.run_sync.await_args.args[0].__name__ == "create_all"
        mock_ext.assert_awaited_once()
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_init_database_rolls_back_on_failure(self) -> None:
        """Session failures during init should trigger rollback and re-raise."""
        connection = FakeConnection()
        engine = FakeEngine("postgresql", connection)
        session = SimpleNamespace(commit=AsyncMock(side_effect=RuntimeError("boom")), rollback=AsyncMock())

        with patch.object(db_init_module, "engine", engine):
            with patch.object(db_init_module, "create_pgvector_extension", new_callable=AsyncMock):
                with patch.object(db_init_module, "async_session_maker", return_value=FakeSessionContext(session)):
                    with pytest.raises(RuntimeError, match="boom"):
                        await db_init_module.init_database()

        session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reset_database_requires_postgres(self) -> None:
        """reset_database() should reject non-PostgreSQL engines."""
        engine = FakeEngine("sqlite", FakeConnection())

        with patch.object(db_init_module, "engine", engine):
            with pytest.raises(RuntimeError, match="only supports PostgreSQL"):
                await db_init_module.reset_database()

    @pytest.mark.asyncio
    async def test_reset_database_executes_full_reset_on_postgres(self) -> None:
        """reset_database() should recreate public schema and extension on PostgreSQL."""
        connection = FakeConnection()
        engine = FakeEngine("postgresql", connection)

        with patch.object(db_init_module, "engine", engine):
            await db_init_module.reset_database()

        assert connection.execute.await_count == 3
        executed = [str(call.args[0]) for call in connection.execute.await_args_list]
        assert "DROP SCHEMA public CASCADE" in executed[0]
        assert "CREATE SCHEMA public" in executed[1]
        assert "CREATE EXTENSION IF NOT EXISTS vector" in executed[2]
        connection.commit.assert_awaited_once()
