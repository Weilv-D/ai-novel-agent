"""Agent chat request/response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """Request schema for agent chat."""

    project_id: str = Field(..., description="Project UUID")
    message: str = Field(..., min_length=1, description="User message")
    history: list[dict[str, str]] = Field(default_factory=list, description="Chat history")
    context: dict[str, Any] = Field(default_factory=dict, description="Extra context data")


class AgentChatResponse(BaseModel):
    """Response schema for agent chat."""

    message: str = Field(..., description="Agent response message")
    suggestions: list[dict[str, Any]] = Field(default_factory=list, description="Generated suggestions")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Agent metadata")


class AutoSummarizeRequest(BaseModel):
    """Request schema for auto-summarize."""

    project_id: str
    chapter_id: str
    content: str = Field(..., min_length=1)


class AutoSummarizeResponse(BaseModel):
    """Response schema for auto-summarize."""

    memories: list[dict[str, Any]]
    count: int


class ContinuityCheckRequest(BaseModel):
    """Request schema for continuity check."""

    project_id: str
    content: str = Field(..., min_length=1)
