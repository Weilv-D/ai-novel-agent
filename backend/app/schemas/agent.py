"""Schemas for the agent workflow and legacy chat endpoints."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Backend schema additions for agent workflow
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
CapabilitySourceRoleLiteral = Literal["planner", "researcher", "writer", "editor", "continuity", "executor"]
SubtaskStatusLiteral = Literal["planned", "completed", "failed", "skipped"]
PermissionLevelLiteral = Literal["read_search", "standard_write", "high_risk_write"]
RiskLevelLiteral = Literal["low", "medium", "high"]
VerificationStatusLiteral = Literal["pending", "passed", "failed", "skipped"]
ExecutionPhaseLiteral = Literal["plan", "build_validation"]
ExecutionModeLiteral = Literal["restricted", "gated"]
RetryStrategyLiteral = Literal["service_only", "planner_then_service_fallback"]
ConfirmationGateLiteral = Literal["none", "single", "double"]
CapabilityKindLiteral = Literal["read_search", "planning", "writing", "editing", "verification"]
CapabilityExecutionStatusLiteral = Literal["planned", "completed", "failed", "skipped"]
RiskPolicyIdLiteral = Literal[
    "create_only",
    "standard_updates",
    "content_append",
    "content_rewrite",
    "long_form_overwrite",
    "multi_object_write",
]
RiskPolicyScopeLiteral = Literal["operation", "run"]
ChildUnitRoleLiteral = Literal["planner", "researcher", "writer", "editor", "continuity", "executor"]
ChildUnitStageLiteral = Literal["preview", "pre_execution", "execution"]
PlannerHistoryModeLiteral = Literal["recent_window", "checkpoint_delta"]
InlineEditOperationLiteral = Literal["rewrite", "expand", "condense", "change_pov"]
PipelineStageLiteral = Literal["research", "brief", "draft", "polish", "continuity_precheck", "plan_ready"]
PipelineStepStatusLiteral = Literal["planned", "completed", "failed", "skipped", "warning"]

AgentStreamEventTypeLiteral = Literal[
    "status",
    "thinking",
    "operation_progress",
    "pipeline_stage",
    "verification",
    "message_chunk",
    "result",
    "error",
]


class AgentStreamEvent(BaseModel):
    """SSE event payload for real-time agent process streaming."""

    type: AgentStreamEventTypeLiteral
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stage: str | None = None
    message: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


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


class AgentCapabilityExecutionRecordResponse(BaseModel):
    """Execution record for one internal capability."""

    record_id: str
    source_role: CapabilitySourceRoleLiteral
    status: CapabilityExecutionStatusLiteral
    tool_scope: list[str] = Field(default_factory=list)
    input_summary: str | None = None
    output_summary: str | None = None
    attempt_count: int = 1


class AgentCapabilityPolicyResponse(BaseModel):
    """Stable policy contract for one internal capability."""

    execution_phase: Literal["plan", "build"]
    source_role: CapabilitySourceRoleLiteral
    confirmation_gate: ConfirmationGateLiteral
    internal_only: bool = True
    requires_confirmation: bool = False


class AgentCapabilityResponse(BaseModel):
    """One stable internal capability exposed with the run contract."""

    capability_id: str
    name: str
    kind: CapabilityKindLiteral
    description: str
    tool_scope: list[str] = Field(default_factory=list)
    policy: AgentCapabilityPolicyResponse
    execution_record: AgentCapabilityExecutionRecordResponse | None = None


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


class AgentPipelineStepResponse(BaseModel):
    """One visible pipeline step for prose-oriented planning."""

    id: str
    role: SubtaskRoleLiteral
    stage: PipelineStageLiteral
    status: PipelineStepStatusLiteral
    summary: str
    warnings: list[str] = Field(default_factory=list)
    facts_used: list[str] = Field(default_factory=list)


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
    pipeline_steps: list[AgentPipelineStepResponse] = Field(default_factory=list)
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
    compact_policy: "AgentCompactPolicyResponse | None" = None
    compaction_boundary: "AgentCompactionBoundaryResponse | None" = None
    active_bundle_contract: "AgentActiveBundleContractResponse | None" = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentCompactPolicyResponse(BaseModel):
    """Stable compact policy applied by the thread planner."""

    policy_version: str
    message_threshold: int
    run_threshold: int
    char_threshold: int
    recent_window_limit: int
    checkpoint_delta_limit: int


class AgentRetainedWindowResponse(BaseModel):
    """Concrete history slice retained for one planner invocation."""

    history_mode: PlannerHistoryModeLiteral
    message_count: int
    character_count: int
    retained_message_limit: int
    oldest_message_id: UUID | None = None
    newest_message_id: UUID | None = None
    checkpoint_id: UUID | None = None
    compact_policy_version: str | None = None
    roles: list[str] = Field(default_factory=list)


class AgentCompactionBoundaryResponse(BaseModel):
    """Boundary metadata captured when a checkpoint was created."""

    history_mode: PlannerHistoryModeLiteral
    source_message_count: int
    source_run_count: int


class AgentActiveBundleCollectionsResponse(BaseModel):
    """Collection limits and realized counts included in the planner bundle."""

    characters_count: int = 0
    characters_limit: int = 0
    world_settings_count: int = 0
    world_settings_limit: int = 0
    volumes_count: int = 0
    volumes_limit: int = 0
    chapters_count: int = 0
    chapters_limit: int = 0
    current_scenes_count: int = 0
    current_scenes_limit: int = 0
    recent_run_digest_count: int = 0
    recent_run_digest_limit: int = 0


class AgentActiveBundleContractResponse(BaseModel):
    """Stable description of which context sections were assembled for planning."""

    contract_version: str
    source: Literal["live_context", "checkpoint_plus_live_context", "checkpoint_snapshot"]
    included_sections: list[str] = Field(default_factory=list)
    focused_object_types: list[str] = Field(default_factory=list)
    checkpoint_id: UUID | None = None
    includes_thread_summary: bool = False
    includes_recent_run_digest: bool = False
    collections: AgentActiveBundleCollectionsResponse


class AgentPlannerWindowResponse(BaseModel):
    """Resolved planner input window for one run."""

    history_mode: PlannerHistoryModeLiteral
    history_message_count: int
    retained_message_limit: int
    checkpoint_id: UUID | None = None
    checkpoint_available: bool = False
    compact_policy_version: str | None = None


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
    child_units: list["AgentExecutionChildUnitResponse"] = Field(default_factory=list)
    capabilities: list[AgentCapabilityResponse] = Field(default_factory=list)


class AgentExecutionChildUnitResponse(BaseModel):
    """Stable contract for one internal child unit inside a workflow phase."""

    unit_id: str
    role: ChildUnitRoleLiteral
    phase: Literal["plan", "build"]
    stage: ChildUnitStageLiteral
    mode: ExecutionModeLiteral
    title: str
    description: str
    tool_scope: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    operation_positions: list[int] = Field(default_factory=list)
    confirmation_gate: ConfirmationGateLiteral
    requires_confirmation: bool = False
    internal_only: bool = True


class AgentExecutionContractResponse(BaseModel):
    """Stable child unit contract surfaced with each run."""

    registry_version: str
    phases: list[AgentExecutionPhaseResponse] = Field(default_factory=list)


class AgentCapabilityRegistryResponse(BaseModel):
    """Stable registry of capability contracts available to the workflow."""

    registry_version: str
    capabilities: list[AgentCapabilityResponse] = Field(default_factory=list)


class AgentRiskPolicyResponse(BaseModel):
    """Stable risk classification policy exposed independently from one run."""

    policy_id: RiskPolicyIdLiteral
    name: str
    scope: RiskPolicyScopeLiteral
    description: str
    risk_level: RiskLevelLiteral
    confirmation_gate: ConfirmationGateLiteral
    requires_secondary_confirmation: bool = False
    tool_scope: list[str] = Field(default_factory=list)


class AgentAppliedRiskPolicyResponse(BaseModel):
    """One policy application recorded on a concrete run."""

    policy_id: RiskPolicyIdLiteral
    name: str
    scope: RiskPolicyScopeLiteral
    description: str
    risk_level: RiskLevelLiteral
    confirmation_gate: ConfirmationGateLiteral
    requires_secondary_confirmation: bool = False
    matched_operation_positions: list[int] = Field(default_factory=list)


class AgentRiskPolicyRegistryResponse(BaseModel):
    """Stable registry of risk policies used by the run classifier."""

    policy_version: str
    policies: list[AgentRiskPolicyResponse] = Field(default_factory=list)


class AgentRunRiskSummaryResponse(BaseModel):
    """Stable run-level aggregation of write risk and confirmation gates."""

    policy_version: str
    overall_risk_level: RiskLevelLiteral
    confirmation_gate: ConfirmationGateLiteral
    requires_confirmation: bool
    requires_secondary_confirmation: bool
    total_operations: int = 0
    low_risk_operation_count: int = 0
    medium_risk_operation_count: int = 0
    high_risk_operation_count: int = 0
    high_risk_operation_positions: list[int] = Field(default_factory=list)
    secondary_confirmation_operation_positions: list[int] = Field(default_factory=list)
    applied_policies: list[AgentAppliedRiskPolicyResponse] = Field(default_factory=list)
    summary: str


class AgentPlanBasisEntityVersionResponse(BaseModel):
    """One entity version checkpoint captured when the plan was created."""

    entity_type: str
    entity_id: UUID
    updated_at: datetime


class AgentPlanBasisResponse(BaseModel):
    """Freshness metadata for one run."""

    entity_versions: list[AgentPlanBasisEntityVersionResponse] = Field(default_factory=list)
    context_fingerprint: str


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
    risk_summary: AgentRunRiskSummaryResponse | None = None
    compact_policy: AgentCompactPolicyResponse | None = None
    planner_window: AgentPlannerWindowResponse | None = None
    retained_window: AgentRetainedWindowResponse | None = None
    active_bundle_contract: AgentActiveBundleContractResponse | None = None
    plan_expires_at: datetime | None = None
    plan_basis: AgentPlanBasisResponse | None = None
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

    project_id: UUID = Field(..., description="Project UUID")
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

    project_id: UUID
    chapter_id: UUID
    content: str = Field(..., min_length=1)


class AutoSummarizeResponse(BaseModel):
    """Response schema for legacy auto-summarize."""

    memories: list[dict[str, Any]]
    count: int


class ContinuityCheckRequest(BaseModel):
    """Request schema for legacy continuity check."""

    project_id: UUID
    content: str = Field(..., min_length=1)


class InlineEditRequest(BaseModel):
    """Request schema for inline selection editing."""

    text: str = Field(..., min_length=1, max_length=3000)
    operation: InlineEditOperationLiteral
    context: dict[str, Any] = Field(default_factory=dict)
