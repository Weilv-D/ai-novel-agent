"""Tests for exception handlers."""

import pytest
from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppException,
    BadRequestException,
    ConflictException,
    NotFoundException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)


class TestAppException:
    """Tests for AppException."""

    def test_app_exception_defaults(self):
        """Test AppException with default values."""
        exc = AppException("Test error")
        assert exc.message == "Test error"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.details == {}

    def test_app_exception_with_status_code(self):
        """Test AppException with custom status code."""
        exc = AppException("Test error", status_code=status.HTTP_400_BAD_REQUEST)
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_app_exception_with_details(self):
        """Test AppException with details."""
        details = {"field": "value"}
        exc = AppException("Test error", details=details)
        assert exc.details == details


class TestSpecificExceptions:
    """Tests for specific exception classes."""

    def test_not_found_exception(self):
        """Test NotFoundException."""
        exc = NotFoundException("Resource not found")
        assert exc.message == "Resource not found"
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_bad_request_exception(self):
        """Test BadRequestException."""
        exc = BadRequestException("Invalid input")
        assert exc.message == "Invalid input"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_conflict_exception(self):
        """Test ConflictException."""
        exc = ConflictException("Duplicate resource")
        assert exc.message == "Duplicate resource"
        assert exc.status_code == status.HTTP_409_CONFLICT


class TestExceptionHandlers:
    """Tests for exception handlers."""

    @pytest.mark.asyncio
    async def test_app_exception_handler(self):
        """Test AppException handler returns correct response."""
        request = Request({"type": "http", "method": "GET", "url": "/"})  # type: ignore[arg-type]
        exc = AppException("Test error", status_code=400, details={"key": "value"})

        response = await app_exception_handler(request, exc)

        assert response.status_code == 400
        body = response.body.decode()
        assert "Test error" in body
        assert "key" in body
        assert "value" in body

    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test HTTPException handler returns correct response."""
        request = Request({"type": "http", "method": "GET", "url": "/"})  # type: ignore[arg-type]
        exc = HTTPException(status_code=404, detail="Not found")

        response = await http_exception_handler(request, exc)

        assert response.status_code == 404
        body = response.body.decode()
        assert "Not found" in body

    @pytest.mark.asyncio
    async def test_generic_exception_handler(self):
        """Test generic exception handler returns 500."""
        request = Request({"type": "http", "method": "GET", "url": "/"})  # type: ignore[arg-type]
        exc = ValueError("Unexpected error")

        response = await generic_exception_handler(request, exc)

        assert response.status_code == 500
        body = response.body.decode()
        assert "Internal server error" in body


class TestIntegration:
    """Integration tests for exception handling."""

    def test_app_exception_in_endpoint(self):
        """Test AppException is handled correctly in an endpoint."""
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.add_exception_handler(AppException, app_exception_handler)

        @test_app.get("/test-app-exception")
        async def test_endpoint():
            raise AppException("Custom error", status_code=418)

        client = TestClient(test_app)
        response = client.get("/test-app-exception")

        assert response.status_code == 418
        data = response.json()
        assert "error" in data
        assert data["error"]["message"] == "Custom error"

    def test_http_exception_in_endpoint(self):
        """Test HTTPException is handled correctly in an endpoint."""
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.add_exception_handler(HTTPException, http_exception_handler)

        @test_app.get("/test-http-exception")
        async def test_endpoint():
            raise HTTPException(status_code=403, detail="Forbidden")

        client = TestClient(test_app)
        response = client.get("/test-http-exception")

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["message"] == "Forbidden"

    def test_generic_exception_in_endpoint(self):
        """Test generic exception is handled correctly in an endpoint."""
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.add_exception_handler(Exception, generic_exception_handler)

        @test_app.get("/test-generic-exception")
        async def test_endpoint():
            raise ValueError("Unexpected error")

        client = TestClient(test_app, raise_server_exceptions=False)
        response = client.get("/test-generic-exception")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["message"] == "Internal server error"
