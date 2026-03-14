"""Health endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Test health check endpoint."""
    with (
        patch("app.api.v1.health.get_database_status", new=AsyncMock(return_value="healthy")),
        patch("app.api.v1.health.get_redis_status", new=AsyncMock(return_value="unavailable")),
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["mode"] == "single_user"
    assert data["auth_required"] is False
    assert data["personal_user_email"] == "writer@local"
    assert data["database"] == "healthy"
    assert data["redis"] == "unavailable"


@pytest.mark.asyncio
async def test_health_check_uses_current_settings(client: AsyncClient) -> None:
    """Test health endpoint reflects the current runtime auth configuration."""
    with (
        patch("app.api.v1.health.get_settings") as mock_get_settings,
        patch("app.api.v1.health.get_database_status", new=AsyncMock(return_value="healthy")),
        patch("app.api.v1.health.get_redis_status", new=AsyncMock(return_value="healthy")),
    ):
        mock_get_settings.return_value.app_version = "9.9.9"
        mock_get_settings.return_value.admin_api_key = "secret-key"
        mock_get_settings.return_value.api_key_header = "X-Personal-Key"
        mock_get_settings.return_value.personal_user_email = "me@example.com"

        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "9.9.9"
    assert data["auth_required"] is True
    assert data["api_key_header"] == "X-Personal-Key"
    assert data["personal_user_email"] == "me@example.com"
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """Test root endpoint."""
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
