"""Tests for runtime support modules such as logging, DB session helpers, and app lifespan."""

from __future__ import annotations

import importlib.util
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.db as db_module
from app import main as main_module
from app.core import logging as logging_module


def _load_isolated_db_runtime_module():
    """Load app.db.__init__ into an isolated module to avoid mutating global test state."""
    spec = importlib.util.spec_from_file_location("tests._isolated_app_db_runtime", db_module.__file__)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeSessionContext:
    """Async context manager returning a prebuilt session."""

    def __init__(self, session: object) -> None:
        self.session = session

    async def __aenter__(self) -> object:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeConnection:
    """Async-shaped DB connection used by init_db tests."""

    def __init__(self) -> None:
        self.execute = AsyncMock()


class FakeBeginContext:
    """Async context manager returning a fake DB connection."""

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeEngine:
    """Engine stub exposing begin() and dispose()."""

    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.dispose = AsyncMock()

    def begin(self) -> FakeBeginContext:
        return FakeBeginContext(self.connection)


class TestLoggingSupport:
    """Covers development and production logging setup branches."""

    def test_setup_logging_uses_console_renderer_in_development(self) -> None:
        settings = SimpleNamespace(debug=True, is_production=False)

        with patch("app.core.logging.logging.basicConfig") as mock_basic_config:
            with patch("app.core.logging.structlog.configure") as mock_configure:
                logging_module.setup_logging(settings)

        mock_basic_config.assert_called_once()
        processors = mock_configure.call_args.kwargs["processors"]
        assert processors[-1].__class__.__name__ == "ConsoleRenderer"

    def test_setup_logging_uses_json_renderer_in_production(self) -> None:
        settings = SimpleNamespace(debug=False, is_production=True)

        with patch("app.core.logging.logging.basicConfig") as mock_basic_config:
            with patch("app.core.logging.structlog.configure") as mock_configure:
                logging_module.setup_logging(settings)

        mock_basic_config.assert_called_once()
        processors = mock_configure.call_args.kwargs["processors"]
        assert processors[-1].__class__.__name__ == "JSONRenderer"

    def test_get_logger_delegates_to_structlog(self) -> None:
        fake_logger = MagicMock()
        with patch("app.core.logging.structlog.get_logger", return_value=fake_logger) as mock_get_logger:
            assert logging_module.get_logger("api") is fake_logger
        mock_get_logger.assert_called_once_with("api")


class TestDbRuntimeHelpers:
    """Covers get_db(), init_db(), and close_db()."""

    @pytest.mark.asyncio
    async def test_get_db_commits_and_closes_on_success(self) -> None:
        runtime_module = _load_isolated_db_runtime_module()
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock(), close=AsyncMock())

        with patch.object(runtime_module, "async_session_maker", return_value=FakeSessionContext(session)):
            dependency = runtime_module.get_db()
            yielded = await anext(dependency)
            assert yielded is session
            with pytest.raises(StopAsyncIteration):
                await anext(dependency)

        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()
        session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_db_rolls_back_and_closes_when_consumer_raises(self) -> None:
        runtime_module = _load_isolated_db_runtime_module()
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock(), close=AsyncMock())

        with patch.object(runtime_module, "async_session_maker", return_value=FakeSessionContext(session)):
            dependency = runtime_module.get_db()
            await anext(dependency)
            with pytest.raises(RuntimeError, match="boom"):
                await dependency.athrow(RuntimeError("boom"))

        session.commit.assert_not_awaited()
        session.rollback.assert_awaited_once()
        session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_db_and_close_db_delegate_to_engine(self) -> None:
        runtime_module = _load_isolated_db_runtime_module()
        connection = FakeConnection()
        engine = FakeEngine(connection)

        with patch.object(runtime_module, "engine", engine):
            await runtime_module.init_db()
            await runtime_module.close_db()

        connection.execute.assert_awaited_once()
        assert "SELECT 1" in str(connection.execute.await_args.args[0])
        engine.dispose.assert_awaited_once()


class TestMainModule:
    """Covers FastAPI lifespan hooks and the root endpoint."""

    @pytest.mark.asyncio
    async def test_lifespan_runs_startup_and_shutdown_hooks(self) -> None:
        with patch("app.main.setup_logging") as mock_setup_logging:
            with patch("app.main.init_db", new_callable=AsyncMock) as mock_init_db:
                with patch("app.main.init_database", new_callable=AsyncMock) as mock_init_database:
                    with patch.object(main_module.cache_service, "init", new_callable=AsyncMock) as mock_cache_init:
                        with patch.object(main_module.cache_service, "close", new_callable=AsyncMock) as mock_cache_close:
                            with patch("app.main.close_db", new_callable=AsyncMock) as mock_close_db:
                                with patch.object(main_module.logger, "info") as mock_logger_info:
                                    async with main_module.lifespan(MagicMock()):
                                        pass

        mock_setup_logging.assert_called_once_with(main_module.settings)
        mock_init_db.assert_awaited_once()
        mock_init_database.assert_awaited_once()
        mock_cache_init.assert_awaited_once()
        mock_cache_close.assert_awaited_once()
        mock_close_db.assert_awaited_once()
        assert mock_logger_info.call_count == 2

    @pytest.mark.asyncio
    async def test_root_returns_metadata(self) -> None:
        payload = await main_module.root()

        assert payload["message"] == "AI Novel Agent API"
        assert payload["docs"] == "/docs"
        assert payload["version"]
