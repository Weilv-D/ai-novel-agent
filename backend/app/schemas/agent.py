"""Schemas for the agent workflow and legacy chat endpoints."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

RunStatusLiteral = Literal[
    "draft",
    "awaiting_confirmation",
    "awaiting_high_risk_confirmation",
    "executing",
    "completed",
    "failed",
    "cancelled",
    "superseded",
]
OperationStatusLiteral = Literal["planned", "executed", "failed", "cancelled"]
MessageRoleLiteral = Literal["user", "assistant", "system"]
SubtaskRoleLiteral = Literal["planner", "researcher", "writer", "editor", "continuity"]
SubtaskStatusLiteral = Literal["planned", "completed", "failed", "skipped"]
PermissionLevelLiteral = Literal["read_search", "standard_write", "high_risk_write"]
RiskLevelLiteral = Literal["low", "medium", "high"]
VerificationStatusLiteral = Literal["pending", "passed", "failed", "skipped"]


class OperationPreview(BaseModel):
    """Preview payload shown before execution."""

    changed_fields: list[str] = Field(default_factory=list)
    before_summary: str | None = None
    after_summary: str | None = None
    diff: str | None = None
    reason: str | None = None


class AgentThreadCreateRequest(BaseModel):
    """Create or fetch the default thread for a project."""

    project_id: UUID


class AgentMessageResponse(BaseModel):
    """Message persisted in an agent thread."""

    id: UUID
    thread_id: UUID
    role: MessageRoleLiteral
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AgentThreadResponse(BaseModel):
    """Thread metadata."""

    id: UUID
    project_id: UUID
    title: str
    is_default: bool
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AgentOperationResponse(BaseModel):
    """A single planned or executed operation."""

    id: UUID
    run_id: UUID
    position: int
    tool_name: str
    target_type: str | None = None
    target_id: UUID | None = None
    target_display: str | None = None
    description: str
    reason: str | None = None
    payload: dict[str, Any]
    preview: OperationPreview
    permission_level: PermissionLevelLiteral
    risk_level: RiskLevelLiteral
    requires_secondary_confirmation: bool
    status: OperationStatusLiteral
    verification_status: VerificationStatusLiteral
    verification_summary: str | None = None
    execution_result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentSubtaskResponse(BaseModel):
    """Internal subtask summary exposed with a run."""

    id: UUID
    run_id: UUID
    position: int
    role: SubtaskRoleLiteral
    title: str
    status: SubtaskStatusLiteral
    summary: str | None = None
    error_message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentRunResponse(BaseModel):
    """An executable plan generated from one user request."""

    id: UUID
    thread_id: UUID
    project_id: UUID
    user_message_id: UUID | None = None
    assistant_message_id: UUID | None = None
    revision_of_run_id: UUID | None = None
    status: RunStatusLiteral
    summary: str | None = None
    error_message: str | None = None
    warning_message: str | None = None
    verification_status: VerificationStatusLiteral
    verification_summary: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    confirmed_at: datetime | None = None
    secondary_confirmed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    operations: list[AgentOperationResponse] = Field(default_factory=list)
    subtasks: list[AgentSubtaskResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True, "populate_by_name": True}


class AgentThreadStateResponse(BaseModel):
    """Thread view used by the Agent Workspace."""

    thread: AgentThreadResponse
    messages: list[AgentMessageResponse] = Field(default_factory=list)
    recent_runs: list[AgentRunResponse] = Field(default_factory=list)
    current_run: AgentRunResponse | None = None


class AgentThreadMessageRequest(BaseModel):
    """User message sent into a thread."""

    content: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


class AgentThreadMessageResponse(BaseModel):
    """Planner response for a new thread message."""

    thread: AgentThreadResponse
    user_message: AgentMessageResponse
    assistant_message: AgentMessageResponse
    run: AgentRunResponse | None = None


class AgentRunActionResponse(BaseModel):
    """Response for confirm/cancel actions."""

    run: AgentRunResponse


class AgentSkillSummaryResponse(BaseModel):
    """Serializable metadata for one loaded planner or operation skill."""

    name: str
    description: str
    kind: str
    tool_name: str | None = None
    source: str
    payload_contract: str | None = None
    references: list[str] = Field(default_factory=list)


class AgentSkillCatalogResponse(BaseModel):
    """Active planner and operation skill catalog."""

    profile_id: str
    profile_name: str
    builtin: bool
    source_roots: list[str] = Field(default_factory=list)
    planner: AgentSkillSummaryResponse
    operations: list[AgentSkillSummaryResponse] = Field(default_factory=list)


class AgentProfileResponse(BaseModel):
    """Available project-level agent profile."""

    id: str
    name: str
    description: str
    builtin: bool
    root: str


class AgentChatRequest(BaseModel):
    """Legacy request schema for the previous chat endpoint."""

    project_id: str = Field(..., description="Project UUID")
    message: str = Field(..., min_length=1, description="User message")
    history: list[dict[str, str]] = Field(default_factory=list, description="Chat history")
    context: dict[str, Any] = Field(default_factory=dict, description="Extra context data")


class AgentChatResponse(BaseModel):
    """Legacy response schema for the previous chat endpoint."""

    message: str = Field(..., description="Agent response message")
    suggestions: list[dict[str, Any]] = Field(default_factory=list, description="Generated suggestions")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Agent metadata")


class AutoSummarizeRequest(BaseModel):
    """Request schema for legacy auto-summarize."""

    project_id: str
    chapter_id: str
    content: str = Field(..., min_length=1)


class AutoSummarizeResponse(BaseModel):
    """Response schema for legacy auto-summarize."""

    memories: list[dict[str, Any]]
    count: int


class ContinuityCheckRequest(BaseModel):
    """Request schema for legacy continuity check."""

    project_id: str
    content: str = Field(..., min_length=1)
