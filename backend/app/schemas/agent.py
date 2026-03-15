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
ExecutionPhaseLiteral = Literal["plan", "build_validation"]
ExecutionModeLiteral = Literal["restricted", "gated"]
RetryStrategyLiteral = Literal["service_only", "planner_then_service_fallback"]
ConfirmationGateLiteral = Literal["none", "single", "double"]
CapabilityKindLiteral = Literal["read_search", "planning", "writing", "editing", "verification"]


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


class AgentCapabilityResponse(BaseModel):
    """One stable internal capability exposed with the run contract."""

    capability_id: str
    name: str
    kind: CapabilityKindLiteral
    description: str
    tool_scope: list[str] = Field(default_factory=list)


class AgentSubtaskAttemptResponse(BaseModel):
    """One attempt within a child execution unit."""

    attempt_number: int
    source: str
    accepted: bool
    validation_status: Literal["passed", "recovered", "failed"]
    summary: str


class AgentSubtaskTraceResponse(BaseModel):
    """Stable child execution trace for one internal subtask."""

    unit_id: str
    role: SubtaskRoleLiteral
    execution_phase: ExecutionPhaseLiteral
    retry_strategy: RetryStrategyLiteral
    depends_on: list[str] = Field(default_factory=list)
    operation_positions: list[int] = Field(default_factory=list)
    tool_scope: list[str] = Field(default_factory=list)
    input_summary: str | None = None
    output_summary: str | None = None
    attempts: list[AgentSubtaskAttemptResponse] = Field(default_factory=list)


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
    child_trace: AgentSubtaskTraceResponse | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentThreadCheckpointResponse(BaseModel):
    """Compressed thread state snapshot exposed to the workspace."""

    id: UUID
    thread_id: UUID
    profile_id: str
    thread_summary: str
    active_object_bundle: dict[str, Any] = Field(default_factory=dict)
    recent_run_digest: dict[str, Any] = Field(default_factory=dict)
    source_message_count: int
    source_run_count: int
    total_context_characters: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentExecutionPhaseResponse(BaseModel):
    """Stable run-level contract for one workflow phase."""

    phase: Literal["plan", "build"]
    mode: ExecutionModeLiteral
    allowed_permission_levels: list[PermissionLevelLiteral] = Field(default_factory=list)
    tool_scope: list[str] = Field(default_factory=list)
    role_scope: list[SubtaskRoleLiteral] = Field(default_factory=list)
    confirmation_gate: ConfirmationGateLiteral
    requires_confirmation: bool = False
    requires_secondary_confirmation: bool = False
    operation_count: int = 0
    capabilities: list[AgentCapabilityResponse] = Field(default_factory=list)


class AgentExecutionContractResponse(BaseModel):
    """Stable child unit contract surfaced with each run."""

    phases: list[AgentExecutionPhaseResponse] = Field(default_factory=list)


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
    execution_contract: AgentExecutionContractResponse | None = None
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
    latest_checkpoint: AgentThreadCheckpointResponse | None = None


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
