"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.cache import cache_service
from app.core.config import get_settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.db import close_db, init_db
from app.db.init_db import init_database

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    # Initialize logging
    setup_logging(settings)

    # Startup
    logger.info("Starting AI Novel Agent API", version=settings.app_version, environment=settings.environment)

    # Initialize database connection and extensions
    await init_db()
    await init_database()
    await cache_service.init()

    yield

    # Shutdown
    logger.info("Shutting down AI Novel Agent API")
    await cache_service.close()
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered long-form novel writing system with agent-based collaboration",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(AppException, cast(Any, app_exception_handler))
app.add_exception_handler(HTTPException, cast(Any, http_exception_handler))
app.add_exception_handler(Exception, cast(Any, generic_exception_handler))

# Include routers
app.include_router(api_v1_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    current_settings = get_settings()
    return {
        "message": "AI Novel Agent API",
        "version": current_settings.app_version,
        "docs": "/docs",
    }
