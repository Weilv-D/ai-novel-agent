"""Health check schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    mode: str
    auth_required: bool
    api_key_header: str | None = None
    personal_user_email: str | None = None
    database: str | None = None
    redis: str | None = None
