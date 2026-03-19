"""Planner and executor for the project-scoped agent workflow."""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta
from textwrap import dedent
from typing import Any, Literal, cast

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.agent_workflow import (
    AgentMessage,
    AgentMessageRole,
    AgentOperation,
    AgentOperationStatus,
    AgentPermissionLevel,
    AgentRiskLevel,
    AgentRun,
    AgentRunStatus,
    AgentSubtask,
    AgentSubtaskRole,
    AgentSubtaskStatus,
    AgentThread,
    AgentThreadCheckpoint,
    AgentVerificationStatus,
)
from app.models.chapter import Chapter, Scene, Volume
from app.models.character import Character
from app.models.project import Project
from app.models.snapshot import Snapshot
from app.models.world_setting import WorldSetting
from app.schemas.agent import (
    AgentActiveBundleContractResponse,
    AgentCapabilityExecutionRecordResponse,
    AgentCapabilityPolicyResponse,
    AgentCapabilityRegistryResponse,
    AgentCapabilityResponse,
    AgentCompactionBoundaryResponse,
    AgentCompactPolicyResponse,
    AgentExecutionChildUnitResponse,
    AgentExecutionContractResponse,
    AgentExecutionPhaseResponse,
    AgentMessageResponse,
    AgentOperationResponse,
    AgentPipelineStepResponse,
    AgentPlanBasisEntityVersionResponse,
    AgentPlanBasisResponse,
    AgentPlannerWindowResponse,
    AgentProfileResponse,
    AgentRetainedWindowResponse,
    AgentRiskPolicyRegistryResponse,
    AgentRunActionResponse,
    AgentRunResponse,
    AgentRunRiskSummaryResponse,
    AgentSkillCatalogResponse,
    AgentSkillSummaryResponse,
    AgentStreamEvent,
    AgentSubtaskAttemptResponse,
    AgentSubtaskResponse,
    AgentSubtaskTraceResponse,
    AgentThreadCheckpointResponse,
    AgentThreadMessageResponse,
    AgentThreadResponse,
    AgentThreadStateResponse,
    OperationPreview,
)
from app.schemas.chapter import (
    ChapterCreate,
    ChapterUpdate,
    SceneCreate,
    SceneUpdate,
    VolumeCreate,
    VolumeUpdate,
)
from app.schemas.character import CharacterCreate, CharacterUpdate
from app.schemas.project import ProjectUpdate
from app.schemas.world_setting import WorldSettingCreate, WorldSettingUpdate
from app.services.agent_contract import agent_contract_service
from app.services.agent_risk import agent_risk_service
from app.services.agent_skill import AgentSkillBundle, agent_skill_service
from app.services.chapter import chapter_service, scene_service, volume_service
from app.services.character import character_service
from app.services.context_assembler import context_assembler
from app.services.dependency import dependency_service
from app.services.llm import LLMService, llm_service
from app.services.memory import memory_service
from app.services.project import project_service
from app.services.snapshot import snapshot_service
from app.services.world_setting import world_setting_service

logger = logging.getLogger(__name__)

TOOL_NAMES = {
    "update_project_outline",
    "create_character",
    "update_character",
    "create_world_setting",
    "update_world_setting",
    "create_volume",
    "update_volume",
    "create_chapter",
    "update_chapter",
    "write_chapter_content",
    "create_scene",
    "update_scene",
    "write_scene_content",
}
RUN_PREVIEW_STATUSES = {
    AgentRunStatus.DRAFT.value,
    AgentRunStatus.AWAITING_CONFIRMATION.value,
    AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value,
    AgentRunStatus.EXECUTING.value,
}
SUBTASK_SUMMARY_LIMIT = 180
COMPACTION_MESSAGE_THRESHOLD = 24
COMPACTION_RUN_THRESHOLD = 10
COMPACTION_CHAR_THRESHOLD = 9000
RECENT_HISTORY_WINDOW_LIMIT = 12
CHECKPOINT_DELTA_HISTORY_LIMIT = 12
COMPACT_POLICY_VERSION = "2026-03-15.1"
ACTIVE_BUNDLE_CONTRACT_VERSION = "2026-03-15.1"
CHARACTER_CONTEXT_LIMIT = 20
WORLD_SETTING_CONTEXT_LIMIT = 20
VOLUME_CONTEXT_LIMIT = 20
CHAPTER_CONTEXT_LIMIT = 40
SCENE_CONTEXT_LIMIT = 20
RECENT_RUN_DIGEST_LIMIT = 6
HOOK_NAMES = ("PreCompact", "PrePlan", "SubagentStop", "RunStop")
CAPABILITY_REGISTRY_VERSION = "2026-03-15.1"
INTERNAL_READ_SEARCH_TOOLS = (
    "list_project_characters",
    "list_project_world_settings",
    "list_project_volumes",
    "list_project_chapters",
    "list_project_scenes",
    "resolve_current_project",
    "resolve_current_character",
    "resolve_current_world_setting",
    "resolve_current_volume",
    "resolve_current_chapter",
    "resolve_current_scene",
    "load_latest_checkpoint",
)
PLAN_TTL_MINUTES = 30
PROSE_OPERATION_TOOLS = {
    "create_chapter",
    "create_scene",
    "write_chapter_content",
    "write_scene_content",
}


class PlannedOperationSpec(BaseModel):
    """Validated operation returned by the planner."""

    tool_name: str
    description: str = Field(..., min_length=1)
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    """Validated planner output."""

    assistant_message: str = Field(..., min_length=1)
    summary: str | None = None
    warning_message: str | None = None
    operations: list[PlannedOperationSpec] = Field(default_factory=list)
    subtasks: list[PlannedSubtaskSpec] = Field(default_factory=list)


class PlannedSubtaskSpec(BaseModel):
    """Internal subtask emitted by the planner or synthesized by the service."""

    role: Literal["planner", "researcher", "writer", "editor", "continuity"]
    title: str = Field(..., min_length=1)
    summary: str | None = None
    status: Literal["planned", "completed", "failed", "skipped"] = "planned"
    error_message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class HookTraceEntry(BaseModel):
    """Internal lifecycle record for one workflow hook."""

    hook_name: Literal["PreCompact", "PrePlan", "SubagentStop", "RunStop"]
    status: Literal["planned", "completed", "failed", "skipped"] = "planned"
    summary: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class RunBlueprint(BaseModel):
    """Internal blueprint that separates visible operations from internal lifecycle state."""

    assistant_message: str
    summary: str | None = None
    warning_message: str | None = None
    user_visible_operations: list[dict[str, Any]] = Field(default_factory=list)
    internal_subtasks: list[dict[str, Any]] = Field(default_factory=list)
    hook_trace: list[HookTraceEntry] = Field(default_factory=list)


class SubtaskExecutionResult(BaseModel):
    """Normalized internal execution result for one subtask unit."""

    role: Literal["planner", "researcher", "writer", "editor", "continuity"]
    title: str
    status: Literal["planned", "completed", "failed", "skipped"]
    summary: str | None = None
    error_message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class SubtaskExecutionAttempt(BaseModel):
    """One attempt inside a child execution unit."""

    attempt_number: int
    source: str
    accepted: bool
    validation_status: Literal["passed", "recovered", "failed"]
    summary: str


class SubtaskExecutionTrace(BaseModel):
    """Observable execution trace for one internal child unit."""

    unit_id: str
    role: Literal["planner", "researcher", "writer", "editor", "continuity"]
    execution_phase: Literal["plan", "build_validation"]
    retry_strategy: Literal["service_only", "planner_then_service_fallback"]
    depends_on: list[str] = Field(default_factory=list)
    operation_positions: list[int] = Field(default_factory=list)
    tool_scope: list[str] = Field(default_factory=list)
    input_summary: str | None = None
    output_summary: str | None = None
    attempts: list[SubtaskExecutionAttempt] = Field(default_factory=list)


class CapabilityScopeSummary(BaseModel):
    """Internal capability grouping used by workflow phases."""

    capability_id: str
    name: str
    kind: Literal["read_search", "planning", "writing", "editing", "verification"]
    description: str
    tool_scope: list[str] = Field(default_factory=list)
    policy: CapabilityPolicySummary
    execution_record: CapabilityExecutionRecordSummary | None = None


class CapabilityExecutionRecordSummary(BaseModel):
    """Internal execution record for one capability."""

    record_id: str
    source_role: Literal["planner", "researcher", "writer", "editor", "continuity", "executor"]
    status: Literal["planned", "completed", "failed", "skipped"]
    tool_scope: list[str] = Field(default_factory=list)
    input_summary: str | None = None
    output_summary: str | None = None
    attempt_count: int = 1


class CapabilityPolicySummary(BaseModel):
    """Stable capability policy independent of one run."""

    execution_phase: Literal["plan", "build"]
    source_role: Literal["planner", "researcher", "writer", "editor", "continuity", "executor"]
    confirmation_gate: Literal["none", "single", "double"]
    internal_only: bool = True
    requires_confirmation: bool = False


class CRUDAgentThread:
    """Persistence helpers for project threads."""

    async def _sync_default_thread_meta(
        self,
        db: AsyncSession,
        *,
        thread: AgentThread,
        project: Project,
    ) -> None:
        next_meta = dict(thread.meta or {})
        if next_meta.get("project_name") != project.name or next_meta.get("profile_id") != project.agent_profile_id:
            next_meta["project_name"] = project.name
            next_meta["profile_id"] = project.agent_profile_id
            thread.meta = next_meta
            await db.flush()

    async def get(self, db: AsyncSession, thread_id: uuid.UUID) -> AgentThread:
        result = await db.execute(select(AgentThread).where(AgentThread.id == thread_id))
        thread = result.scalar_one_or_none()
        if thread is None:
            raise NotFoundException("Agent thread not found")
        return thread

    async def get_default_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
    ) -> AgentThread | None:
        result = await db.execute(
            select(AgentThread)
            .where(AgentThread.project_id == project_id, AgentThread.is_default.is_(True))
            .order_by(desc(AgentThread.updated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_default(
        self,
        db: AsyncSession,
        *,
        project: Project,
    ) -> AgentThread:
        existing = await self.get_default_by_project(db, project_id=project.id)
        if existing is not None:
            await self._sync_default_thread_meta(db, thread=existing, project=project)
            return existing

        thread = AgentThread(
            project_id=project.id,
            title=f"{project.name} Agent Workspace",
            is_default=True,
            meta={
                "project_name": project.name,
                "profile_id": project.agent_profile_id,
            },
        )
        try:
            transaction = db.begin_nested()
            async with AsyncExitStack() as stack:
                if hasattr(transaction, "__aenter__"):
                    await stack.enter_async_context(cast(Any, transaction))
                else:
                    stack.enter_context(cast(Any, transaction))
                db.add(thread)
                await db.flush()
        except IntegrityError:
            existing = await self.get_default_by_project(db, project_id=project.id)
            if existing is None:
                raise
            await self._sync_default_thread_meta(db, thread=existing, project=project)
            return existing

        await db.refresh(thread)
        return thread


class CRUDAgentMessage:
    """Persistence helpers for thread messages."""

    async def get(self, db: AsyncSession, message_id: uuid.UUID) -> AgentMessage:
        result = await db.execute(select(AgentMessage).where(AgentMessage.id == message_id))
        message = result.scalar_one_or_none()
        if message is None:
            raise NotFoundException("Agent message not found")
        return message

    async def create(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        role: str,
        content: str,
        meta: dict[str, Any] | None = None,
    ) -> AgentMessage:
        message = AgentMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            meta=meta or {},
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message

    async def list_by_thread(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        limit: int = 50,
    ) -> list[AgentMessage]:
        result = await db.execute(
            select(AgentMessage)
            .where(AgentMessage.thread_id == thread_id)
            .order_by(AgentMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent_history(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        limit: int = 12,
    ) -> list[AgentMessage]:
        result = await db.execute(
            select(AgentMessage)
            .where(AgentMessage.thread_id == thread_id)
            .order_by(AgentMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(result.scalars().all())))

    async def list_after_offset(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        offset: int,
        limit: int = COMPACTION_MESSAGE_THRESHOLD,
    ) -> list[AgentMessage]:
        result = await db.execute(
            select(AgentMessage)
            .where(AgentMessage.thread_id == thread_id)
            .order_by(AgentMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


class CRUDAgentRun:
    """Persistence helpers for agent runs."""

    async def get(self, db: AsyncSession, run_id: uuid.UUID) -> AgentRun:
        result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            raise NotFoundException("Agent run not found")
        return run

    async def create(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        project_id: uuid.UUID,
        user_message_id: uuid.UUID | None,
        assistant_message_id: uuid.UUID | None,
        revision_of_run_id: uuid.UUID | None,
        summary: str | None,
        warning_message: str | None,
        meta: dict[str, Any] | None = None,
    ) -> AgentRun:
        run = AgentRun(
            thread_id=thread_id,
            project_id=project_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            revision_of_run_id=revision_of_run_id,
            status=AgentRunStatus.AWAITING_CONFIRMATION.value,
            summary=summary,
            warning_message=warning_message,
            meta=meta or {},
        )
        db.add(run)
        await db.flush()
        await db.refresh(run)
        return run

    async def list_recent_by_thread(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        limit: int = 10,
    ) -> list[AgentRun]:
        result = await db.execute(
            select(AgentRun)
            .where(AgentRun.thread_id == thread_id)
            .order_by(desc(AgentRun.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_pending(self, db: AsyncSession, *, thread_id: uuid.UUID) -> AgentRun | None:
        result = await db.execute(
            select(AgentRun)
            .where(
                AgentRun.thread_id == thread_id,
                AgentRun.status.in_(
                    [
                        AgentRunStatus.DRAFT.value,
                        AgentRunStatus.AWAITING_CONFIRMATION.value,
                        AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value,
                    ]
                ),
            )
            .order_by(desc(AgentRun.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def supersede_pending_runs(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        keep_run_id: uuid.UUID | None = None,
    ) -> list[uuid.UUID]:
        result = await db.execute(
            select(AgentRun)
            .where(
                AgentRun.thread_id == thread_id,
                AgentRun.status.in_(
                    [
                        AgentRunStatus.DRAFT.value,
                        AgentRunStatus.AWAITING_CONFIRMATION.value,
                        AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value,
                    ]
                ),
            )
            .order_by(desc(AgentRun.created_at))
        )
        superseded_ids: list[uuid.UUID] = []
        for run in result.scalars().all():
            if keep_run_id is not None and run.id == keep_run_id:
                continue
            run.status = AgentRunStatus.SUPERSEDED.value
            run.completed_at = datetime.now(UTC)
            superseded_ids.append(run.id)
        if superseded_ids:
            await db.flush()
        return superseded_ids


class CRUDAgentOperation:
    """Persistence helpers for run operations."""

    async def create_many(
        self,
        db: AsyncSession,
        *,
        run_id: uuid.UUID,
        operations: list[dict[str, Any]],
    ) -> list[AgentOperation]:
        created: list[AgentOperation] = []
        for index, operation in enumerate(operations, start=1):
            op = AgentOperation(
                run_id=run_id,
                position=index,
                tool_name=operation["tool_name"],
                target_type=operation.get("target_type"),
                target_id=operation.get("target_id"),
                target_display=operation.get("target_display"),
                description=operation["description"],
                reason=operation.get("reason"),
                payload=operation["payload"],
                preview=operation["preview"],
                permission_level=operation.get("permission_level", AgentPermissionLevel.STANDARD_WRITE.value),
                risk_level=operation.get("risk_level", AgentRiskLevel.MEDIUM.value),
                requires_secondary_confirmation=bool(operation.get("requires_secondary_confirmation", False)),
                status=AgentOperationStatus.PLANNED.value,
                verification_status=operation.get("verification_status", AgentVerificationStatus.PENDING.value),
                verification_summary=operation.get("verification_summary"),
                preview_content_hash=operation.get("preview_content_hash"),
                execution_result=operation.get("execution_result"),
            )
            db.add(op)
            created.append(op)
        await db.flush()
        for op in created:
            await db.refresh(op)
        return created

    async def list_by_run(self, db: AsyncSession, *, run_id: uuid.UUID) -> list[AgentOperation]:
        result = await db.execute(
            select(AgentOperation)
            .where(AgentOperation.run_id == run_id)
            .order_by(AgentOperation.position.asc())
        )
        return list(result.scalars().all())


class CRUDAgentSubtask:
    """Persistence helpers for internal subtasks."""

    async def create_many(
        self,
        db: AsyncSession,
        *,
        run_id: uuid.UUID,
        subtasks: list[dict[str, Any]],
    ) -> list[AgentSubtask]:
        created: list[AgentSubtask] = []
        for index, subtask in enumerate(subtasks, start=1):
            record = AgentSubtask(
                run_id=run_id,
                position=index,
                role=subtask["role"],
                title=subtask["title"],
                status=subtask["status"],
                summary=subtask.get("summary"),
                error_message=subtask.get("error_message"),
                meta=subtask.get("meta", {}),
            )
            db.add(record)
            created.append(record)
        await db.flush()
        for record in created:
            await db.refresh(record)
        return created

    async def list_by_run(self, db: AsyncSession, *, run_id: uuid.UUID) -> list[AgentSubtask]:
        result = await db.execute(
            select(AgentSubtask)
            .where(AgentSubtask.run_id == run_id)
            .order_by(AgentSubtask.position.asc())
        )
        return list(result.scalars().all())

    async def get_by_role(
        self,
        db: AsyncSession,
        *,
        run_id: uuid.UUID,
        role: str,
    ) -> AgentSubtask | None:
        result = await db.execute(
            select(AgentSubtask)
            .where(AgentSubtask.run_id == run_id, AgentSubtask.role == role)
            .limit(1)
        )
        return result.scalar_one_or_none()


class CRUDAgentThreadCheckpoint:
    """Persistence helpers for compressed thread state."""

    async def create(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        profile_id: str,
        thread_summary: str,
        active_object_bundle: dict[str, Any],
        recent_run_digest: dict[str, Any],
        source_message_count: int,
        source_run_count: int,
        total_context_characters: int,
    ) -> AgentThreadCheckpoint:
        checkpoint = AgentThreadCheckpoint(
            thread_id=thread_id,
            profile_id=profile_id,
            thread_summary=thread_summary,
            active_object_bundle=active_object_bundle,
            recent_run_digest=recent_run_digest,
            source_message_count=source_message_count,
            source_run_count=source_run_count,
            total_context_characters=total_context_characters,
        )
        db.add(checkpoint)
        await db.flush()
        await db.refresh(checkpoint)
        return checkpoint

    async def latest_by_thread(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
    ) -> AgentThreadCheckpoint | None:
        result = await db.execute(
            select(AgentThreadCheckpoint)
            .where(AgentThreadCheckpoint.thread_id == thread_id)
            .order_by(desc(AgentThreadCheckpoint.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()


def _json_ready(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _serialize_model(model: Any) -> dict[str, Any]:
    return {
        attr.key: _json_ready(getattr(model, attr.key))
        for attr in model.__mapper__.column_attrs
    }


def _excerpt(text: str | None, *, length: int = 220) -> str | None:
    if text is None:
        return None
    compact = text.strip()
    if not compact:
        return None
    if len(compact) <= length:
        return compact
    return f"{compact[: length - 1]}…"


def _build_diff(before: str | None, after: str | None) -> str | None:
    before_text = before or ""
    after_text = after or ""
    if before_text == after_text:
        return None
    diff = difflib.unified_diff(
        before_text.splitlines(),
        after_text.splitlines(),
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(diff)


def _hash_text(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _extract_json_object(text: str) -> dict[str, Any]:
    match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
    if match:
        candidate = match.group(1).strip()
        try:
            loaded = json.loads(candidate)
            if isinstance(loaded, dict):
                return cast(dict[str, Any], loaded)
        except json.JSONDecodeError:
            pass

    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            loaded = json.loads(text[index:])
            if isinstance(loaded, dict):
                return cast(dict[str, Any], loaded)
        except json.JSONDecodeError:
            continue
    raise BadRequestException("Planner response was not valid JSON")


class AgentWorkflowService:
    """High-level workflow for planner/executor-style agent interactions."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self.llm = llm or llm_service
        self.thread_store = CRUDAgentThread()
        self.message_store = CRUDAgentMessage()
        self.run_store = CRUDAgentRun()
        self.operation_store = CRUDAgentOperation()
        self.subtask_store = CRUDAgentSubtask()
        self.checkpoint_store = CRUDAgentThreadCheckpoint()

    async def get_or_create_thread_response(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
    ) -> AgentThreadResponse:
        project = await project_service.get(db, id=project_id)
        thread = await self.thread_store.get_or_create_default(db, project=project)
        return self._thread_response(thread)

    async def get_thread_state_response(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
    ) -> AgentThreadStateResponse:
        thread = await self.thread_store.get(db, thread_id)
        messages = await self.message_store.list_by_thread(db, thread_id=thread.id, limit=60)
        runs = await self.run_store.list_recent_by_thread(db, thread_id=thread.id, limit=8)
        latest_checkpoint = await self.checkpoint_store.latest_by_thread(db, thread_id=thread.id)
        current_run: AgentRunResponse | None = None
        recent_runs: list[AgentRunResponse] = []
        for run in runs:
            serialized = await self._run_response(db, run)
            if current_run is None and run.status in RUN_PREVIEW_STATUSES:
                current_run = serialized
            recent_runs.append(serialized)
        return AgentThreadStateResponse(
            thread=self._thread_response(thread),
            messages=[self._message_response(message) for message in messages],
            recent_runs=recent_runs,
            current_run=current_run,
            latest_checkpoint=self._checkpoint_response(latest_checkpoint) if latest_checkpoint is not None else None,
        )

    async def get_profile_catalog_response(self) -> list[AgentProfileResponse]:
        """Expose all available agent profiles."""
        return [
            AgentProfileResponse(
                id=profile.id,
                name=profile.name,
                description=profile.description,
                builtin=profile.builtin,
                root=str(profile.root),
            )
            for profile in agent_skill_service.list_profiles()
        ]

    async def get_capability_registry_response(self) -> AgentCapabilityRegistryResponse:
        """Expose the stable capability registry used by the workflow."""
        registry = self._capability_registry()
        return AgentCapabilityRegistryResponse(
            registry_version=CAPABILITY_REGISTRY_VERSION,
            capabilities=[self._capability_response(entry) for entry in registry.values()],
        )

    async def get_risk_policy_registry_response(
        self,
        db: AsyncSession | None = None,
        *,
        project_id: uuid.UUID | None = None,
        profile_id: str | None = None,
    ) -> AgentRiskPolicyRegistryResponse:
        """Expose the stable risk policy registry used by the workflow."""
        resolved_profile_id = profile_id or "default"
        if project_id is not None:
            if db is None:
                raise BadRequestException("Database session is required when project_id is provided")
            project = await project_service.get(db, id=project_id)
            resolved_profile_id = project.agent_profile_id
        return agent_risk_service.get_registry_response(profile_id=resolved_profile_id)

    async def get_skill_catalog_response(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID | None = None,
    ) -> AgentSkillCatalogResponse:
        """Expose the active planner and operation skills for a project profile."""
        profile_id = "default"
        if project_id is not None:
            project = await project_service.get(db, id=project_id)
            profile_id = project.agent_profile_id
        bundle = agent_skill_service.load_bundle(profile_id=profile_id)
        summaries = [AgentSkillSummaryResponse(**summary.__dict__) for summary in bundle.catalog()]
        planner = next(summary for summary in summaries if summary.kind == "planner")
        operations = [summary for summary in summaries if summary.kind == "operation"]
        return AgentSkillCatalogResponse(
            profile_id=bundle.profile.id,
            profile_name=bundle.profile.name,
            builtin=bundle.profile.builtin,
            source_roots=[str(root) for root in bundle.roots],
            planner=planner,
            operations=operations,
        )

    async def create_planned_run(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> AgentThreadMessageResponse:
        thread = await self.thread_store.get(db, thread_id)
        project = await project_service.get(db, id=thread.project_id)
        request_context = context or {}
        context_request_context = {**request_context, "_user_message": content}
        prior_run = await self.run_store.get_latest_pending(db, thread_id=thread.id)
        full_history = await self.message_store.list_by_thread(db, thread_id=thread.id, limit=60)
        recent_runs = await self.run_store.list_recent_by_thread(db, thread_id=thread.id, limit=20)
        profile_id = project.agent_profile_id
        skill_bundle = agent_skill_service.load_bundle(profile_id=profile_id)

        user_message = await self.message_store.create(
            db,
            thread_id=thread.id,
            role=AgentMessageRole.USER.value,
            content=content,
            meta={"context": request_context},
        )

        checkpoint, precompact_hook = await self._maybe_compact_thread(
            db,
            thread=thread,
            project=project,
            profile_id=profile_id,
            history=full_history,
            recent_runs=recent_runs,
            request_context=request_context,
        )
        history, history_mode = await self._planner_history(
            db,
            thread_id=thread.id,
            latest_checkpoint=checkpoint,
            current_user_message_id=user_message.id,
        )
        context_data = await self._load_project_context(
            db,
            project=project,
            request_context=context_request_context,
            latest_checkpoint=checkpoint,
        )
        context_data["retained_window"] = self._retained_window_payload(
            history=history,
            history_mode=history_mode,
            latest_checkpoint=checkpoint,
        )
        context_data["planner_window"] = {
            "history_mode": history_mode,
            "history_message_count": len(history),
            "retained_message_limit": (
                CHECKPOINT_DELTA_HISTORY_LIMIT if history_mode == "checkpoint_delta" else RECENT_HISTORY_WINDOW_LIMIT
            ),
            "checkpoint_id": str(checkpoint.id) if checkpoint is not None else None,
            "checkpoint_available": checkpoint is not None,
            "compact_policy_version": COMPACT_POLICY_VERSION,
        }
        context_data["active_bundle_contract"] = self._active_bundle_contract_payload_for_run(
            context_data=context_data,
            latest_checkpoint=checkpoint,
        )
        preplan_hook = self._build_pre_plan_hook(
            project=project,
            context_data=context_data,
            latest_checkpoint=checkpoint,
            history=history,
            history_mode=history_mode,
        )
        planner_output = await self._plan_with_llm(
            user_message=content,
            context_data=context_data,
            history=history,
            prior_run=prior_run,
            skill_bundle=skill_bundle,
        )

        assistant_message = await self.message_store.create(
            db,
            thread_id=thread.id,
            role=AgentMessageRole.ASSISTANT.value,
            content=planner_output.assistant_message,
            meta={"summary": planner_output.summary},
        )

        planned_operations = await self._prepare_operations(
            db,
            project_id=thread.project_id,
            request_context=request_context,
            operations=planner_output.operations,
            context_data=context_data,
        )
        classified_operations = self._classify_operations(planned_operations, profile_id=profile_id)
        run_precheck = self._plan_precheck_from_operations(classified_operations)
        risk_summary = agent_risk_service.build_run_risk_summary(
            classified_operations,
            profile_id=profile_id,
        )
        planned_subtasks = self._build_subtasks(
            planner_output=planner_output,
            operations=classified_operations,
            context_data=context_data,
            latest_checkpoint=checkpoint,
        )
        execution_contract_payload = self._build_execution_contract_payload(
            operations=classified_operations,
            subtasks=planned_subtasks,
            context_data=context_data,
            latest_checkpoint=checkpoint,
        )
        subagent_stop_hook = self._validate_blueprint(
            operations=classified_operations,
            subtasks=planned_subtasks,
        )
        blueprint = RunBlueprint(
            assistant_message=planner_output.assistant_message,
            summary=planner_output.summary,
            warning_message=self._merge_warning_messages(
                planner_output.warning_message,
                [str(run_precheck["summary"])] if str(run_precheck.get("status")) == "warn" else [],
            ),
            user_visible_operations=classified_operations,
            internal_subtasks=planned_subtasks,
            hook_trace=[precompact_hook, preplan_hook, subagent_stop_hook],
        )
        plan_basis = await self._build_plan_basis(
            db,
            project=project,
            request_context=request_context,
            context_data=context_data,
            operations=classified_operations,
        )
        plan_expires_at = datetime.now(UTC) + timedelta(minutes=PLAN_TTL_MINUTES)

        run = await self.run_store.create(
            db,
            thread_id=thread.id,
            project_id=thread.project_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            revision_of_run_id=prior_run.id if prior_run is not None else None,
            summary=blueprint.summary,
            warning_message=blueprint.warning_message,
            meta={
                "request_context": request_context,
                "raw_operation_count": len(blueprint.user_visible_operations),
                "profile_id": profile_id,
                "checkpoint_id": str(checkpoint.id) if checkpoint is not None else None,
                "compact_policy": self._compact_policy_payload(),
                "planner_window": context_data["planner_window"],
                "retained_window": context_data["retained_window"],
                "active_bundle_contract": context_data["active_bundle_contract"],
                "skill_snapshot": self._build_skill_snapshot(skill_bundle, blueprint.user_visible_operations),
                "hook_trace": [entry.model_dump(mode="json") for entry in blueprint.hook_trace],
                "permission_matrix": execution_contract_payload,
                "risk_summary": risk_summary.model_dump(mode="json"),
                "plan_expires_at": plan_expires_at.isoformat(),
                "plan_basis": plan_basis,
                "plan_precheck": run_precheck,
                "blueprint": {
                    "operation_count": len(blueprint.user_visible_operations),
                    "subtask_count": len(blueprint.internal_subtasks),
                    "subtask_roles": [str(subtask["role"]) for subtask in blueprint.internal_subtasks],
                },
            },
        )
        await self.operation_store.create_many(db, run_id=run.id, operations=blueprint.user_visible_operations)
        await self.subtask_store.create_many(db, run_id=run.id, subtasks=blueprint.internal_subtasks)
        await self.run_store.supersede_pending_runs(db, thread_id=thread.id, keep_run_id=run.id)
        if str(run_precheck.get("status")) == "block":
            run.status = AgentRunStatus.FAILED.value
            run.error_message = str(run_precheck.get("summary") or "计划级连续性预检失败")
            run.completed_at = datetime.now(UTC)
            run.verification_status = AgentVerificationStatus.FAILED.value
            run.verification_summary = run.error_message
            await db.flush()

        return AgentThreadMessageResponse(
            thread=self._thread_response(thread),
            user_message=self._message_response(user_message),
            assistant_message=self._message_response(assistant_message),
            run=await self._run_response(db, run),
        )

    async def stream_planned_run(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentStreamEvent]:
        """Stream agent planning process with real-time status updates."""
        yield AgentStreamEvent(
            type="status",
            stage="init",
            message="正在初始化 Agent 工作流...",
            detail={"thread_id": str(thread_id)},
        )

        thread = await self.thread_store.get(db, thread_id)
        project = await project_service.get(db, id=thread.project_id)
        request_context = context or {}
        context_request_context = {**request_context, "_user_message": content}

        yield AgentStreamEvent(
            type="status",
            stage="load_context",
            message="正在加载项目上下文...",
            detail={"project_id": str(project.id), "project_name": project.name},
        )

        prior_run = await self.run_store.get_latest_pending(db, thread_id=thread.id)
        full_history = await self.message_store.list_by_thread(db, thread_id=thread.id, limit=60)
        recent_runs = await self.run_store.list_recent_by_thread(db, thread_id=thread.id, limit=20)
        profile_id = project.agent_profile_id
        skill_bundle = agent_skill_service.load_bundle(profile_id=profile_id)

        user_message = await self.message_store.create(
            db,
            thread_id=thread.id,
            role=AgentMessageRole.USER.value,
            content=content,
            meta={"context": request_context},
        )

        checkpoint, precompact_hook = await self._maybe_compact_thread(
            db,
            thread=thread,
            project=project,
            profile_id=profile_id,
            history=full_history,
            recent_runs=recent_runs,
            request_context=request_context,
        )

        yield AgentStreamEvent(
            type="status",
            stage="compact_check",
            message="线程压缩检查完成",
            detail={
                "checkpoint_id": str(checkpoint.id) if checkpoint else None,
                "precompact_status": precompact_hook.status,
            },
        )

        history, history_mode = await self._planner_history(
            db,
            thread_id=thread.id,
            latest_checkpoint=checkpoint,
            current_user_message_id=user_message.id,
        )
        context_data = await self._load_project_context(
            db,
            project=project,
            request_context=context_request_context,
            latest_checkpoint=checkpoint,
        )
        context_data["retained_window"] = self._retained_window_payload(
            history=history,
            history_mode=history_mode,
            latest_checkpoint=checkpoint,
        )
        context_data["planner_window"] = {
            "history_mode": history_mode,
            "history_message_count": len(history),
            "retained_message_limit": (
                CHECKPOINT_DELTA_HISTORY_LIMIT if history_mode == "checkpoint_delta" else RECENT_HISTORY_WINDOW_LIMIT
            ),
            "checkpoint_id": str(checkpoint.id) if checkpoint is not None else None,
            "checkpoint_available": checkpoint is not None,
            "compact_policy_version": COMPACT_POLICY_VERSION,
        }
        context_data["active_bundle_contract"] = self._active_bundle_contract_payload_for_run(
            context_data=context_data,
            latest_checkpoint=checkpoint,
        )
        preplan_hook = self._build_pre_plan_hook(
            project=project,
            context_data=context_data,
            latest_checkpoint=checkpoint,
            history=history,
            history_mode=history_mode,
        )

        yield AgentStreamEvent(
            type="thinking",
            stage="planning",
            message="Agent 正在分析您的请求并规划操作...",
            detail={
                "history_count": len(history),
                "history_mode": history_mode,
                "profile_id": profile_id,
            },
        )

        planner_output = await self._plan_with_llm(
            user_message=content,
            context_data=context_data,
            history=history,
            prior_run=prior_run,
            skill_bundle=skill_bundle,
        )

        yield AgentStreamEvent(
            type="thinking",
            stage="plan_complete",
            message=f"规划完成，共 {len(planner_output.operations)} 个操作",
            detail={
                "summary": planner_output.summary,
                "operation_count": len(planner_output.operations),
                "operations": [
                    {"tool_name": op.tool_name, "description": op.description}
                    for op in planner_output.operations
                ],
            },
        )

        assistant_message = await self.message_store.create(
            db,
            thread_id=thread.id,
            role=AgentMessageRole.ASSISTANT.value,
            content=planner_output.assistant_message,
            meta={"summary": planner_output.summary},
        )

        yield AgentStreamEvent(
            type="status",
            stage="prepare_operations",
            message="正在准备操作预览...",
            detail={"operation_count": len(planner_output.operations)},
        )

        pipeline_events: list[AgentStreamEvent] = []
        planned_operations = await self._prepare_operations(
            db,
            project_id=thread.project_id,
            request_context=request_context,
            operations=planner_output.operations,
            context_data=context_data,
            event_sink=pipeline_events,
        )
        for event in pipeline_events:
            yield event

        for i, operation in enumerate(planned_operations):
            yield AgentStreamEvent(
                type="operation_progress",
                stage="prepare",
                message=f"准备操作 {i + 1}/{len(planned_operations)}: {operation.get('tool_name', 'unknown')}",
                detail={
                    "position": i + 1,
                    "total": len(planned_operations),
                    "tool_name": operation.get("tool_name"),
                    "target_display": operation.get("target_display"),
                },
            )

        classified_operations = self._classify_operations(planned_operations, profile_id=profile_id)
        run_precheck = self._plan_precheck_from_operations(classified_operations)
        risk_summary = agent_risk_service.build_run_risk_summary(
            classified_operations,
            profile_id=profile_id,
        )

        yield AgentStreamEvent(
            type="status",
            stage="risk_assessment",
            message=f"风险评估完成: {risk_summary.overall_risk_level} 风险",
            detail={
                "overall_risk_level": risk_summary.overall_risk_level,
                "total_operations": risk_summary.total_operations,
                "high_risk_count": risk_summary.high_risk_operation_count,
                "confirmation_gate": risk_summary.confirmation_gate,
            },
        )

        planned_subtasks = self._build_subtasks(
            planner_output=planner_output,
            operations=classified_operations,
            context_data=context_data,
            latest_checkpoint=checkpoint,
        )
        execution_contract_payload = self._build_execution_contract_payload(
            operations=classified_operations,
            subtasks=planned_subtasks,
            context_data=context_data,
            latest_checkpoint=checkpoint,
        )
        subagent_stop_hook = self._validate_blueprint(
            operations=classified_operations,
            subtasks=planned_subtasks,
        )
        blueprint = RunBlueprint(
            assistant_message=planner_output.assistant_message,
            summary=planner_output.summary,
            warning_message=self._merge_warning_messages(
                planner_output.warning_message,
                [str(run_precheck["summary"])] if str(run_precheck.get("status")) == "warn" else [],
            ),
            user_visible_operations=classified_operations,
            internal_subtasks=planned_subtasks,
            hook_trace=[precompact_hook, preplan_hook, subagent_stop_hook],
        )
        plan_basis = await self._build_plan_basis(
            db,
            project=project,
            request_context=request_context,
            context_data=context_data,
            operations=classified_operations,
        )
        plan_expires_at = datetime.now(UTC) + timedelta(minutes=PLAN_TTL_MINUTES)

        run = await self.run_store.create(
            db,
            thread_id=thread.id,
            project_id=thread.project_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            revision_of_run_id=prior_run.id if prior_run is not None else None,
            summary=blueprint.summary,
            warning_message=blueprint.warning_message,
            meta={
                "request_context": request_context,
                "raw_operation_count": len(blueprint.user_visible_operations),
                "profile_id": profile_id,
                "checkpoint_id": str(checkpoint.id) if checkpoint is not None else None,
                "compact_policy": self._compact_policy_payload(),
                "planner_window": context_data["planner_window"],
                "retained_window": context_data["retained_window"],
                "active_bundle_contract": context_data["active_bundle_contract"],
                "skill_snapshot": self._build_skill_snapshot(skill_bundle, blueprint.user_visible_operations),
                "hook_trace": [entry.model_dump(mode="json") for entry in blueprint.hook_trace],
                "permission_matrix": execution_contract_payload,
                "risk_summary": risk_summary.model_dump(mode="json"),
                "plan_expires_at": plan_expires_at.isoformat(),
                "plan_basis": plan_basis,
                "plan_precheck": run_precheck,
                "blueprint": {
                    "operation_count": len(blueprint.user_visible_operations),
                    "subtask_count": len(blueprint.internal_subtasks),
                    "subtask_roles": [str(subtask["role"]) for subtask in blueprint.internal_subtasks],
                },
            },
        )
        await self.operation_store.create_many(db, run_id=run.id, operations=blueprint.user_visible_operations)
        await self.subtask_store.create_many(db, run_id=run.id, subtasks=blueprint.internal_subtasks)
        await self.run_store.supersede_pending_runs(db, thread_id=thread.id, keep_run_id=run.id)
        if str(run_precheck.get("status")) == "block":
            run.status = AgentRunStatus.FAILED.value
            run.error_message = str(run_precheck.get("summary") or "计划级连续性预检失败")
            run.completed_at = datetime.now(UTC)
            run.verification_status = AgentVerificationStatus.FAILED.value
            run.verification_summary = run.error_message
            await db.flush()
            yield AgentStreamEvent(
                type="error",
                stage="planning_precheck",
                message=run.error_message,
                detail={"status": "block", "code": "planning_precheck_blocked"},
            )

        yield AgentStreamEvent(
            type="message_chunk",
            stage="assistant_message",
            message=planner_output.assistant_message,
            detail={},
        )

        yield AgentStreamEvent(
            type="result",
            stage="complete",
            message="Agent 规划完成，等待用户确认",
            detail={
                "thread": self._thread_response(thread).model_dump(mode="json"),
                "user_message": self._message_response(user_message).model_dump(mode="json"),
                "assistant_message": self._message_response(assistant_message).model_dump(mode="json"),
                "run": (await self._run_response(db, run)).model_dump(mode="json"),
            },
        )

    async def get_run_response(self, db: AsyncSession, *, run_id: uuid.UUID) -> AgentRunResponse:
        run = await self.run_store.get(db, run_id)
        return await self._run_response(db, run)

    async def cancel_run_response(
        self,
        db: AsyncSession,
        *,
        run_id: uuid.UUID,
    ) -> AgentRunActionResponse:
        run = await self.run_store.get(db, run_id)
        if run.status not in {
            AgentRunStatus.DRAFT.value,
            AgentRunStatus.AWAITING_CONFIRMATION.value,
            AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value,
        }:
            raise BadRequestException("Only draft or awaiting-confirmation runs can be cancelled")
        run.status = AgentRunStatus.CANCELLED.value
        run.completed_at = datetime.now(UTC)
        run.verification_status = AgentVerificationStatus.SKIPPED.value
        run.verification_summary = "Run was cancelled before execution."
        self._update_capability_execution_record(
            run,
            phase_name="build",
            capability_id="operation_execution",
            status="skipped",
            output_summary="Run was cancelled before execution.",
        )
        operations = await self.operation_store.list_by_run(db, run_id=run.id)
        for operation in operations:
            operation.status = AgentOperationStatus.CANCELLED.value
            operation.verification_status = AgentVerificationStatus.SKIPPED.value
            operation.verification_summary = "Run was cancelled before execution."
        await db.flush()
        return AgentRunActionResponse(run=await self._run_response(db, run))

    async def confirm_run_response(
        self,
        db: AsyncSession,
        *,
        run_id: uuid.UUID,
    ) -> AgentRunActionResponse:
        run = await self.run_store.get(db, run_id)
        if run.status != AgentRunStatus.AWAITING_CONFIRMATION.value:
            raise BadRequestException("Run is not awaiting confirmation")
        await self._assert_run_plan_freshness(db, run=run)

        operations = await self.operation_store.list_by_run(db, run_id=run.id)
        if any(operation.requires_secondary_confirmation for operation in operations):
            run.status = AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value
            run.confirmed_at = datetime.now(UTC)
            run.warning_message = "检测到高风险写入。请再次确认后才会真正执行。"
            await db.flush()
            return AgentRunActionResponse(run=await self._run_response(db, run))

        return await self._execute_run(db, run=run, operations=operations)

    async def confirm_high_risk_run_response(
        self,
        db: AsyncSession,
        *,
        run_id: uuid.UUID,
    ) -> AgentRunActionResponse:
        """Confirm and execute a high-risk run after the second approval."""
        run = await self.run_store.get(db, run_id)
        if run.status != AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value:
            raise BadRequestException("Run is not awaiting high-risk confirmation")
        await self._assert_run_plan_freshness(db, run=run)
        operations = await self.operation_store.list_by_run(db, run_id=run.id)
        run.secondary_confirmed_at = datetime.now(UTC)
        return await self._execute_run(db, run=run, operations=operations)

    async def _execute_run(
        self,
        db: AsyncSession,
        *,
        run: AgentRun,
        operations: list[AgentOperation],
    ) -> AgentRunActionResponse:
        """Execute a planned run and apply the verification gate."""
        continuity_subtask = await self.subtask_store.get_by_role(
            db,
            run_id=run.id,
            role=AgentSubtaskRole.CONTINUITY.value,
        )

        run_id_value = run.id
        run.status = AgentRunStatus.EXECUTING.value
        now = datetime.now(UTC)
        run.confirmed_at = run.confirmed_at or now
        run.started_at = now
        await db.flush()

        failing_operation_id: uuid.UUID | None = None
        current_operation: AgentOperation | None = None
        failing_execution_result: dict[str, Any] | None = None
        refresh_warnings: list[str] = []
        try:
            request_context = cast(dict[str, Any], run.meta.get("request_context", {}))
            continuity_summary = self._check_continuity_gate(operations)
            if continuity_subtask is not None:
                continuity_subtask.summary = continuity_summary
            if continuity_summary != "通过":
                if continuity_subtask is not None:
                    continuity_subtask.status = AgentSubtaskStatus.FAILED.value
                    continuity_subtask.error_message = continuity_summary
                raise BadRequestException(f"Continuity check blocked execution: {continuity_summary}")
            if continuity_subtask is not None:
                continuity_subtask.status = AgentSubtaskStatus.COMPLETED.value

            for operation in operations:
                current_operation = operation
                failing_operation_id = operation.id
                await self._execute_operation(
                    db,
                    project_id=run.project_id,
                    request_context=request_context,
                    operation=operation,
                )
                try:
                    await self._verify_operation(
                        db,
                        project_id=run.project_id,
                        operation=operation,
                    )
                    refresh_warning = await self._refresh_operation_artifacts(
                        db,
                        project_id=run.project_id,
                        request_context=request_context,
                        operation=operation,
                    )
                    if refresh_warning:
                        refresh_warnings.append(refresh_warning)
                finally:
                    if current_operation.id == failing_operation_id:
                        failing_execution_result = dict(current_operation.execution_result or {})
            run.status = AgentRunStatus.COMPLETED.value
            run.completed_at = datetime.now(UTC)
            run.warning_message = self._merge_warning_messages(
                self._execution_warning(operations),
                refresh_warnings,
            )
            run.verification_status, run.verification_summary = self._aggregate_run_verification(
                operations,
                continuity_subtask=continuity_subtask,
            )
            self._update_capability_execution_record(
                run,
                phase_name="build",
                capability_id="operation_execution",
                status="completed",
                output_summary=run.verification_summary or "Build phase completed.",
            )
            self._upsert_run_hook_trace(
                run,
                HookTraceEntry(
                    hook_name="RunStop",
                    status="completed",
                    summary=run.verification_summary,
                    meta={
                        "verification_status": run.verification_status,
                        "operation_count": len(operations),
                    },
                ),
            )
            if run.verification_status != AgentVerificationStatus.PASSED.value:
                raise BadRequestException(run.verification_summary or "Run verification failed")
            await db.flush()
            completed_run = await self.run_store.get(db, run_id_value)
            return AgentRunActionResponse(run=await self._run_response(db, completed_run))
        except Exception as exc:
            logger.exception("Agent run %s failed", run_id_value)
            await db.rollback()
            failed_run = await self.run_store.get(db, run_id_value)
            failed_run.status = AgentRunStatus.FAILED.value
            failed_run.error_message = str(exc)
            failed_run.completed_at = datetime.now(UTC)
            failed_run.verification_status = AgentVerificationStatus.FAILED.value
            failed_run.verification_summary = str(exc)
            self._update_capability_execution_record(
                failed_run,
                phase_name="build",
                capability_id="operation_execution",
                status="failed",
                output_summary=str(exc),
            )
            self._upsert_run_hook_trace(
                failed_run,
                HookTraceEntry(
                    hook_name="RunStop",
                    status="failed",
                    summary=str(exc),
                    meta={"operation_id": str(failing_operation_id) if failing_operation_id is not None else None},
                ),
            )
            if failing_operation_id is not None:
                failed_operation = await self._safe_get_operation(db, operation_id=failing_operation_id)
                if failed_operation is not None:
                    failed_operation.status = AgentOperationStatus.FAILED.value
                    failed_operation.error_message = str(exc)
                    failed_operation.verification_status = AgentVerificationStatus.FAILED.value
                    failed_operation.verification_summary = str(exc)
                    if failing_execution_result is not None:
                        failed_operation.execution_result = dict(failing_execution_result)
            if continuity_subtask is not None:
                failed_continuity = await self.subtask_store.get_by_role(
                    db,
                    run_id=run_id_value,
                    role=AgentSubtaskRole.CONTINUITY.value,
                )
                if failed_continuity is not None and failed_continuity.status != AgentSubtaskStatus.COMPLETED.value:
                    failed_continuity.status = AgentSubtaskStatus.FAILED.value
                    failed_continuity.error_message = str(exc)
            await db.flush()
            return AgentRunActionResponse(run=await self._run_response(db, failed_run))

    async def _load_project_context(
        self,
        db: AsyncSession,
        *,
        project: Project,
        request_context: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None = None,
    ) -> dict[str, Any]:
        return await context_assembler.build_context(
            db,
            project=project,
            request_context=request_context,
            user_message=str(request_context.get("_user_message", "")),
            latest_checkpoint=latest_checkpoint,
            mode="planning",
        )

    async def _planner_history(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        latest_checkpoint: AgentThreadCheckpoint | None,
        current_user_message_id: uuid.UUID,
    ) -> tuple[list[AgentMessage], Literal["recent_window", "checkpoint_delta"]]:
        if latest_checkpoint is None:
            history = await self.message_store.list_recent_history(
                db,
                thread_id=thread_id,
                limit=RECENT_HISTORY_WINDOW_LIMIT,
            )
            history = [message for message in history if message.id != current_user_message_id]
            return history, "recent_window"

        history = await self.message_store.list_after_offset(
            db,
            thread_id=thread_id,
            offset=latest_checkpoint.source_message_count,
            limit=CHECKPOINT_DELTA_HISTORY_LIMIT,
        )
        history = [message for message in history if message.id != current_user_message_id]
        return history, "checkpoint_delta"

    async def _maybe_compact_thread(
        self,
        db: AsyncSession,
        *,
        thread: AgentThread,
        project: Project,
        profile_id: str,
        history: list[AgentMessage],
        recent_runs: list[AgentRun],
        request_context: dict[str, Any],
    ) -> tuple[AgentThreadCheckpoint | None, HookTraceEntry]:
        latest_checkpoint = await self.checkpoint_store.latest_by_thread(db, thread_id=thread.id)
        total_chars = sum(len(message.content) for message in history) + sum(len(run.summary or "") for run in recent_runs)
        should_compact = (
            len(history) >= COMPACTION_MESSAGE_THRESHOLD
            or len(recent_runs) >= COMPACTION_RUN_THRESHOLD
            or total_chars >= COMPACTION_CHAR_THRESHOLD
        )
        if not should_compact:
            return latest_checkpoint, HookTraceEntry(
                hook_name="PreCompact",
                status="skipped",
                summary="线程尚未达到压缩阈值。",
                meta={
                    "message_count": len(history),
                    "run_count": len(recent_runs),
                    "total_context_characters": total_chars,
                    "compact_policy_version": COMPACT_POLICY_VERSION,
                    "recent_window_limit": RECENT_HISTORY_WINDOW_LIMIT,
                    "checkpoint_delta_limit": CHECKPOINT_DELTA_HISTORY_LIMIT,
                },
            )

        if latest_checkpoint is not None:
            if (
                latest_checkpoint.source_message_count >= len(history)
                and latest_checkpoint.source_run_count >= len(recent_runs)
                and latest_checkpoint.total_context_characters >= total_chars
            ):
                return latest_checkpoint, HookTraceEntry(
                    hook_name="PreCompact",
                    status="completed",
                    summary="沿用现有 checkpoint，无需重新压缩。",
                    meta={
                        "checkpoint_id": str(latest_checkpoint.id),
                        "compact_policy_version": COMPACT_POLICY_VERSION,
                        "history_mode": "checkpoint_delta",
                        "recent_window_limit": RECENT_HISTORY_WINDOW_LIMIT,
                        "checkpoint_delta_limit": CHECKPOINT_DELTA_HISTORY_LIMIT,
                    },
                )

        compact_context = {
            "project": {"name": project.name, "genre": project.genre, "summary": project.summary},
            "request_context": request_context,
            "compact_policy": self._compact_policy_payload(),
            "compaction_boundary": {
                "history_mode": "checkpoint_delta",
                "source_message_count": len(history),
                "source_run_count": len(recent_runs),
            },
            "active_bundle_contract": self._active_bundle_contract_payload_for_checkpoint(
                request_context=request_context,
                latest_checkpoint=latest_checkpoint,
                recent_runs=recent_runs,
            ),
        }
        thread_summary = self._summarize_thread(history=history, recent_runs=recent_runs)
        recent_run_digest = {
            "runs": [
                {
                    "id": str(run.id),
                    "status": run.status,
                    "summary": run.summary,
                    "updated_at": run.updated_at.isoformat(),
                }
                for run in recent_runs[:RECENT_RUN_DIGEST_LIMIT]
            ]
        }
        created_checkpoint = await self.checkpoint_store.create(
            db,
            thread_id=thread.id,
            profile_id=profile_id,
            thread_summary=thread_summary,
            active_object_bundle=compact_context,
            recent_run_digest=recent_run_digest,
            source_message_count=len(history),
            source_run_count=len(recent_runs),
            total_context_characters=total_chars,
        )
        return created_checkpoint, HookTraceEntry(
            hook_name="PreCompact",
            status="completed",
            summary="线程达到阈值，已生成新的上下文压缩 checkpoint。",
            meta={
                "checkpoint_id": str(created_checkpoint.id),
                "history_mode": "checkpoint_delta",
                "source_message_count": len(history),
                "source_run_count": len(recent_runs),
                "compact_policy_version": COMPACT_POLICY_VERSION,
                "recent_window_limit": RECENT_HISTORY_WINDOW_LIMIT,
                "checkpoint_delta_limit": CHECKPOINT_DELTA_HISTORY_LIMIT,
            },
        )

    async def _plan_with_llm(
        self,
        *,
        user_message: str,
        context_data: dict[str, Any],
        history: list[AgentMessage],
        prior_run: AgentRun | None,
        skill_bundle: AgentSkillBundle,
    ) -> PlannerOutput:
        from app.core.config import get_settings

        settings = get_settings()
        if settings.agent_e2e_mode == "fixture":
            return await self._plan_with_fixture(user_message=user_message)

        if not self.llm.api_key:
            raise BadRequestException("LLM API key not configured for agent planning")

        history_lines = [
            f"{message.role}: {message.content}"
            for message in history[-8:]
        ]
        previous_plan = "无"
        if prior_run is not None:
            previous_plan = prior_run.summary or "存在待确认计划"

        tool_descriptions = "\n".join(
            f"- {skill.tool_name}: {skill.payload_contract}"
            for skill in skill_bundle.ordered_operations()
            if skill.tool_name and skill.payload_contract
        )
        selected_skills = skill_bundle.select_operations(
            user_message=user_message,
            context_data=context_data,
            prior_summary=previous_plan,
        )
        selected_skill_blocks = "\n\n".join(skill.prompt_block() for skill in selected_skills)
        reference_blocks = "\n\n".join(skill_bundle.load_reference_blocks(selected_skills))
        focus_context = json.dumps(context_data.get("focus_context", {}), ensure_ascii=False, indent=2)
        working_context = json.dumps(context_data.get("working_context", {}), ensure_ascii=False, indent=2)
        thread_context = json.dumps(context_data.get("thread_context", {}), ensure_ascii=False, indent=2)
        memory_facts = "\n".join(
            f"- {item.get('content')} (sim={item.get('similarity')})"
            for item in cast(list[dict[str, Any]], cast(dict[str, Any], context_data.get("memory_context", {})).get("facts", []))
            if item.get("content")
        )
        agent_settings = json.dumps(context_data.get("agent_settings", {}), ensure_ascii=False, indent=2)

        prompt = dedent(
            f"""
            {skill_bundle.planner.prompt_block()}

            项目级风格与质量约束：
            {agent_settings}

            聚焦上下文：
            {focus_context}

            工作上下文：
            {working_context}

            检索到的相关事实：
            {memory_facts or "无"}

            线程上下文：
            {thread_context}

            精简项目清单上下文：
            {json.dumps({
                "project": context_data.get("project", {}),
                "characters": context_data.get("characters", []),
                "world_settings": context_data.get("world_settings", []),
                "volumes": context_data.get("volumes", []),
                "chapters": context_data.get("chapters", []),
                "context_summary": context_data.get("context_summary", {}),
            }, ensure_ascii=False)}

            最近对话：
            {json.dumps(history_lines, ensure_ascii=False)}

            之前待确认计划摘要：
            {json.dumps(previous_plan, ensure_ascii=False)}

            可用工具及 payload 约定：
            {tool_descriptions}

            当前请求相关的 operation skills：
            {selected_skill_blocks}

            补充参考：
            {reference_blocks or "无"}

            输出 JSON 结构：
            {{
              "assistant_message": "给用户的自然语言回复，说明你准备做什么",
              "summary": "计划摘要",
              "warning_message": "可选，提示用户执行后的注意事项",
              "operations": [
                {{
                  "tool_name": "create_character",
                  "description": "创建新人物",
                  "reason": "用户要求新增人物",
                  "payload": {{}}
                }}
              ]
            }}

            用户消息：
            {user_message}
            """
        ).strip()

        result = await self.llm.generate(
            [
                {"role": "system", "content": "你是严谨的多步执行规划器。始终返回 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        parsed = _extract_json_object(result["content"])
        try:
            planner_output = PlannerOutput.model_validate(parsed)
        except ValidationError as exc:
            raise BadRequestException(f"Planner response validation failed: {exc}") from exc

        for operation in planner_output.operations:
            if operation.tool_name not in TOOL_NAMES:
                raise BadRequestException(f"Planner returned unsupported tool '{operation.tool_name}'")

        return planner_output

    async def _plan_with_fixture(self, *, user_message: str) -> PlannerOutput:
        from pathlib import Path

        from app.core.config import get_settings

        settings = get_settings()
        fixture_path = settings.agent_e2e_fixture_path
        if not fixture_path:
            raise BadRequestException("AGENT_E2E_FIXTURE_PATH not configured for fixture mode")

        fixture_file = Path(fixture_path) / "planner-responses.json"
        if not fixture_file.exists():
            raise BadRequestException(f"Fixture file not found: {fixture_file}")

        fixture_data = json.loads(fixture_file.read_text(encoding="utf-8"))

        normalized_message = user_message.strip()
        if normalized_message not in fixture_data:
            raise BadRequestException(
                f"No fixture found for message: '{normalized_message}'. "
                f"Available fixtures: {list(fixture_data.keys())}"
            )

        fixture_response = fixture_data[normalized_message]
        try:
            planner_output = PlannerOutput.model_validate(fixture_response)
        except ValidationError as exc:
            raise BadRequestException(f"Invalid fixture response: {exc}") from exc

        for operation in planner_output.operations:
            if operation.tool_name not in TOOL_NAMES:
                raise BadRequestException(f"Fixture contains unsupported tool '{operation.tool_name}'")

        return planner_output

    async def _prepare_operations(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        request_context: dict[str, Any],
        operations: list[PlannedOperationSpec],
        context_data: dict[str, Any] | None = None,
        event_sink: list[AgentStreamEvent] | None = None,
    ) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []
        for planned_operation in operations:
            normalized = await self._normalize_operation_payload(
                db,
                project_id=project_id,
                request_context=request_context,
                operation=planned_operation,
            )
            prepared.append(normalized)
        if context_data is None:
            return prepared

        enhanced: list[dict[str, Any]] = []
        for index, prepared_operation in enumerate(prepared, start=1):
            enhanced_operation = await self._apply_planning_pipeline_to_operation(
                db,
                project_id=project_id,
                request_context=request_context,
                context_data=context_data,
                operation=prepared_operation,
                operation_position=index,
                event_sink=event_sink,
            )
            if enhanced_operation.get("_rebuild_preview"):
                rebuilt = await self._normalize_operation_payload(
                    db,
                    project_id=project_id,
                    request_context=request_context,
                    operation=PlannedOperationSpec(
                        tool_name=str(enhanced_operation["tool_name"]),
                        description=str(enhanced_operation["description"]),
                        reason=cast(str | None, enhanced_operation.get("reason")),
                        payload=cast(dict[str, Any], enhanced_operation["payload"]),
                    ),
                )
                rebuilt["execution_result"] = enhanced_operation.get("execution_result")
                enhanced.append(rebuilt)
            else:
                enhanced.append(enhanced_operation)

        run_precheck = self._build_run_precheck(enhanced, context_data=context_data)
        for prepared_operation in enhanced:
            execution_result = dict(prepared_operation.get("execution_result") or {})
            execution_result["run_precheck"] = run_precheck
            prepared_operation["execution_result"] = execution_result
        return enhanced

    async def _apply_planning_pipeline_to_operation(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        request_context: dict[str, Any],
        context_data: dict[str, Any],
        operation: dict[str, Any],
        operation_position: int,
        event_sink: list[AgentStreamEvent] | None = None,
    ) -> dict[str, Any]:
        if str(operation["tool_name"]) not in PROSE_OPERATION_TOOLS:
            return operation
        candidate = (self._operation_content_candidate(operation) or "").strip()
        if not candidate:
            return operation

        agent_settings = cast(dict[str, Any], context_data.get("agent_settings", {}))
        pipeline_steps: list[dict[str, Any]] = []
        facts_used = [
            str(item.get("content"))
            for item in cast(list[dict[str, Any]], cast(dict[str, Any], context_data.get("memory_context", {})).get("facts", []))
            if item.get("content")
        ][:5]
        research_summary = (
            f"已装配焦点上下文，命中 {len(facts_used)} 条事实，"
            f"角色 {len(cast(list[Any], cast(dict[str, Any], context_data.get('working_context', {})).get('matched_characters', [])))}，"
            f"设定 {len(cast(list[Any], cast(dict[str, Any], context_data.get('working_context', {})).get('matched_world_settings', [])))}。"
        )
        pipeline_steps.append(
            self._make_pipeline_step(
                role="researcher",
                stage="research",
                status="completed",
                summary=research_summary,
                facts_used=facts_used,
            )
        )
        self._append_pipeline_event(
            event_sink,
            operation_position=operation_position,
            stage="research",
            status="completed",
            summary=research_summary,
        )

        brief_prompt = dedent(
            f"""
            你是中文长篇小说写作总编。请为一个正文写作步骤产出简明写作 brief。
            只返回 4 行以内的中文纯文本，不要列数字序号。

            项目风格约束：
            {json.dumps(agent_settings, ensure_ascii=False)}

            请求上下文：
            {json.dumps(context_data.get("focus_context", {}), ensure_ascii=False)}

            相关事实：
            {json.dumps(facts_used, ensure_ascii=False)}

            当前步骤：
            {json.dumps({
                "tool_name": operation["tool_name"],
                "description": operation["description"],
                "reason": operation.get("reason"),
                "payload": operation["payload"],
            }, ensure_ascii=False)}

            当前候选正文：
            {candidate}
            """
        ).strip()
        brief = (
            await self.llm.generate(
                [
                    {"role": "system", "content": "你是严谨的写作 brief 生成器。只返回简洁中文纯文本。"},
                    {"role": "user", "content": brief_prompt},
                ],
                temperature=0.2,
                max_tokens=260,
            )
        )["content"].strip()
        pipeline_steps.append(
            self._make_pipeline_step(
                role="writer",
                stage="brief",
                status="completed",
                summary=_excerpt(brief, length=220) or "写作 brief 已生成。",
                facts_used=facts_used,
            )
        )
        self._append_pipeline_event(
            event_sink,
            operation_position=operation_position,
            stage="brief",
            status="completed",
            summary=_excerpt(brief, length=120) or "写作 brief 已生成。",
        )

        target_chars = self._target_chars_for_operation(agent_settings=agent_settings, operation=operation)
        draft_prompt = dedent(
            f"""
            你是中文长篇小说正文写手。请根据 brief 重写或补强正文，只返回正文。
            必须遵守：
            - 保留既有事实、人名、地名和核心事件。
            - 保持与原候选接近的篇幅和信息密度。
            - 目标篇幅约 {target_chars} 字，若原文更短则以原文规模为准。
            - 禁止解释、列点、加标题。

            项目风格约束：
            {json.dumps(agent_settings, ensure_ascii=False)}

            写作 brief：
            {brief}

            相关事实：
            {json.dumps(facts_used, ensure_ascii=False)}

            当前候选正文：
            {candidate}
            """
        ).strip()
        drafted_content = (
            await self.llm.generate(
                [
                    {"role": "system", "content": "你是中文长篇小说作者。只返回正文。"},
                    {"role": "user", "content": draft_prompt},
                ],
                temperature=0.45,
                max_tokens=1800,
            )
        )["content"].strip()
        pipeline_steps.append(
            self._make_pipeline_step(
                role="writer",
                stage="draft",
                status="completed",
                summary=f"正文候选已重写，长度 {len(drafted_content)} 字。",
                facts_used=facts_used,
            )
        )
        self._append_pipeline_event(
            event_sink,
            operation_position=operation_position,
            stage="draft",
            status="completed",
            summary=f"正文候选已重写，长度 {len(drafted_content)} 字。",
        )

        polish_prompt = dedent(
            f"""
            你是中文长篇小说润色编辑。请在不改变事实与情节顺序的前提下润色正文，只返回正文。
            重点：
            - 落实风格目标、语气约束与禁忌。
            - 强化动作、画面、节奏和人物说话方式。
            - 术语与设定名词保持一致。

            项目风格约束：
            {json.dumps(agent_settings, ensure_ascii=False)}

            必须保留的事实：
            {json.dumps(facts_used, ensure_ascii=False)}

            待润色正文：
            {drafted_content}
            """
        ).strip()
        polished_content = (
            await self.llm.generate(
                [
                    {"role": "system", "content": "你是中文长篇小说润色编辑。只返回润色后的正文。"},
                    {"role": "user", "content": polish_prompt},
                ],
                temperature=0.25,
                max_tokens=1800,
            )
        )["content"].strip()
        pipeline_steps.append(
            self._make_pipeline_step(
                role="writer",
                stage="polish",
                status="completed",
                summary=f"正文已润色，长度 {len(polished_content)} 字。",
                facts_used=facts_used,
            )
        )
        self._append_pipeline_event(
            event_sink,
            operation_position=operation_position,
            stage="polish",
            status="completed",
            summary=f"正文已润色，长度 {len(polished_content)} 字。",
        )

        precheck = await self._run_planning_continuity_precheck(
            db,
            project_id=project_id,
            request_context=request_context,
            operation=operation,
            operation_position=operation_position,
            content=polished_content,
            facts_used=facts_used,
            agent_settings=agent_settings,
        )
        pipeline_steps.append(
            self._make_pipeline_step(
                role="continuity",
                stage="continuity_precheck",
                status="warning" if precheck["status"] == "warn" else ("failed" if precheck["status"] == "block" else "completed"),
                summary=str(precheck["summary"]),
                warnings=cast(list[str], precheck.get("warnings", [])),
                facts_used=cast(list[str], precheck.get("facts_used", [])),
            )
        )
        self._append_pipeline_event(
            event_sink,
            operation_position=operation_position,
            stage="continuity_precheck",
            status="warning" if precheck["status"] == "warn" else ("failed" if precheck["status"] == "block" else "completed"),
            summary=str(precheck["summary"]),
        )
        pipeline_steps.append(
            self._make_pipeline_step(
                role="writer",
                stage="plan_ready",
                status="completed",
                summary="正文候选已完成研究、起草、润色与连续性预检，可进入确认。",
                warnings=cast(list[str], precheck.get("warnings", [])),
                facts_used=facts_used,
            )
        )
        self._append_pipeline_event(
            event_sink,
            operation_position=operation_position,
            stage="plan_ready",
            status="completed",
            summary="正文候选已完成多阶段规划。",
        )

        next_operation = dict(operation)
        next_payload = dict(cast(dict[str, Any], next_operation.get("payload", {})))
        if str(next_operation["tool_name"]) in {"write_chapter_content", "write_scene_content", "create_chapter", "create_scene"}:
            next_payload["content"] = polished_content
        next_operation["payload"] = next_payload
        next_operation["_rebuild_preview"] = True
        next_operation["execution_result"] = {
            **cast(dict[str, Any], next_operation.get("execution_result") or {}),
            "planning_pipeline": pipeline_steps,
            "planning_precheck": precheck,
            "writing_brief": brief,
        }
        return next_operation

    async def _run_planning_continuity_precheck(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        request_context: dict[str, Any],
        operation: dict[str, Any],
        operation_position: int,
        content: str,
        facts_used: list[str],
        agent_settings: dict[str, Any],
    ) -> dict[str, Any]:
        warnings: list[str] = []
        facts: list[str] = list(facts_used)
        status = "pass"

        forbidden_patterns = [str(item).strip() for item in cast(list[Any], agent_settings.get("forbidden_patterns", [])) if str(item).strip()]
        matched_forbidden = [pattern for pattern in forbidden_patterns if pattern in content]
        if matched_forbidden:
            warnings.append(f"命中风格禁忌：{', '.join(matched_forbidden[:3])}")
            status = "warn"

        payload = cast(dict[str, Any], operation.get("payload", {}))
        if str(operation["tool_name"]) == "create_scene" and payload.get("pov_character_id"):
            try:
                pov_character = await character_service.get(db, id=uuid.UUID(str(payload["pov_character_id"])))
            except Exception:
                return {
                    "status": "block",
                    "summary": "连续性预检失败：POV 人物不存在。",
                    "warnings": [],
                    "facts_used": facts,
                }
            if pov_character.project_id != project_id:
                return {
                    "status": "block",
                    "summary": "连续性预检失败：POV 人物不属于当前项目。",
                    "warnings": [],
                    "facts_used": facts,
                }

        llm_summary = "连续性预检通过。"
        if facts:
            prompt = dedent(
                f"""
                你是小说连续性审核器。请根据正文和事实清单判断是否存在冲突。
                只返回 JSON:
                {{
                  "status": "pass|warn|block",
                  "summary": "一句中文结论",
                  "warnings": ["..."],
                  "facts_used": ["直接引用你实际用到的事实摘要"]
                }}

                模式：{agent_settings.get("continuity_mode", "strict")}
                相关事实：
                {json.dumps(facts, ensure_ascii=False)}

                当前步骤：
                {json.dumps({
                    "operation_position": operation_position,
                    "tool_name": operation["tool_name"],
                    "description": operation["description"],
                    "request_context": request_context,
                }, ensure_ascii=False)}

                正文：
                {content}
                """
            ).strip()
            llm_result = await self.llm.generate(
                [
                    {"role": "system", "content": "你是严谨的小说连续性审核器。始终返回 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=320,
            )
            parsed = _extract_json_object(llm_result["content"])
            llm_status = str(parsed.get("status") or "pass")
            if llm_status in {"pass", "warn", "block"}:
                status = "block" if "block" in {status, llm_status} else ("warn" if "warn" in {status, llm_status} else "pass")
            llm_summary = str(parsed.get("summary") or llm_summary)
            warnings.extend(str(item) for item in cast(list[Any], parsed.get("warnings", [])) if str(item).strip())
            facts = [str(item) for item in cast(list[Any], parsed.get("facts_used", [])) if str(item).strip()] or facts

        return {
            "status": status,
            "summary": llm_summary if status != "warn" or not warnings else f"{llm_summary}；{'；'.join(warnings[:3])}",
            "warnings": list(dict.fromkeys(warnings)),
            "facts_used": facts,
        }

    def _build_run_precheck(
        self,
        operations: list[dict[str, Any]],
        *,
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        duplicate_targets: dict[tuple[str, str], list[int]] = {}
        warnings: list[str] = []
        facts_used: list[str] = []
        for index, operation in enumerate(operations, start=1):
            execution_result = cast(dict[str, Any], operation.get("execution_result") or {})
            planning_precheck = cast(dict[str, Any], execution_result.get("planning_precheck") or {})
            warnings.extend(str(item) for item in cast(list[Any], planning_precheck.get("warnings", [])) if str(item).strip())
            facts_used.extend(str(item) for item in cast(list[Any], planning_precheck.get("facts_used", [])) if str(item).strip())
            if (
                operation.get("target_type")
                and operation.get("target_id")
                and str(operation.get("tool_name")) in {"update_chapter", "write_chapter_content", "update_scene", "write_scene_content"}
            ):
                key = (str(operation["target_type"]), str(operation["target_id"]))
                duplicate_targets.setdefault(key, []).append(index)

        blocking_reasons = [
            f"{target_type}:{target_id} 在同一计划中存在多个正文写入步骤（{positions}）。"
            for (target_type, target_id), positions in duplicate_targets.items()
            if len(positions) > 1
        ]
        if blocking_reasons:
            return {
                "status": "block",
                "summary": "；".join(blocking_reasons),
                "warnings": warnings,
                "facts_used": list(dict.fromkeys(facts_used)),
                "context_summary": context_data.get("context_summary", {}),
            }
        if warnings:
            return {
                "status": "warn",
                "summary": "连续性预检发现需要人工复核的风险。",
                "warnings": list(dict.fromkeys(warnings)),
                "facts_used": list(dict.fromkeys(facts_used)),
                "context_summary": context_data.get("context_summary", {}),
            }
        return {
            "status": "pass",
            "summary": "计划级连续性预检通过。",
            "warnings": [],
            "facts_used": list(dict.fromkeys(facts_used)),
            "context_summary": context_data.get("context_summary", {}),
        }

    def _make_pipeline_step(
        self,
        *,
        role: str,
        stage: str,
        status: str,
        summary: str,
        warnings: list[str] | None = None,
        facts_used: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "id": f"{role}:{stage}:{uuid.uuid4().hex[:8]}",
            "role": role,
            "stage": stage,
            "status": status,
            "summary": summary,
            "warnings": list(warnings or []),
            "facts_used": list(facts_used or []),
        }

    def _append_pipeline_event(
        self,
        event_sink: list[AgentStreamEvent] | None,
        *,
        operation_position: int,
        stage: str,
        status: str,
        summary: str,
    ) -> None:
        if event_sink is None:
            return
        event_sink.append(
            AgentStreamEvent(
                type="pipeline_stage",
                stage=stage,
                message=summary,
                detail={
                    "operation_position": operation_position,
                    "stage": stage,
                    "status": status,
                    "summary": summary,
                },
            )
        )

    def _target_chars_for_operation(
        self,
        *,
        agent_settings: dict[str, Any],
        operation: dict[str, Any],
    ) -> int:
        if str(operation["tool_name"]) in {"create_scene", "write_scene_content"}:
            scene_target = agent_settings.get("scene_target_chars")
            if isinstance(scene_target, int) and scene_target > 0:
                return scene_target
        chapter_target = agent_settings.get("chapter_target_chars")
        if isinstance(chapter_target, int) and chapter_target > 0:
            return chapter_target
        return 6000

    async def _build_plan_basis(
        self,
        db: AsyncSession,
        *,
        project: Project,
        request_context: dict[str, Any],
        context_data: dict[str, Any],
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        entities: dict[tuple[str, uuid.UUID], datetime] = {( "project", project.id): project.updated_at}
        context_targets = [
            ("volume", request_context.get("volume_id")),
            ("chapter", request_context.get("chapter_id")),
            ("scene", request_context.get("scene_id")),
            ("character", request_context.get("character_id")),
            ("world_setting", request_context.get("world_setting_id")),
        ]
        for entity_type, raw_id in context_targets:
            if not raw_id:
                continue
            try:
                entity_id = uuid.UUID(str(raw_id))
            except ValueError:
                continue
            updated_at = await self._resolve_entity_updated_at(db, entity_type=entity_type, entity_id=entity_id)
            if updated_at is not None:
                entities[(entity_type, entity_id)] = updated_at

        for operation in operations:
            target_type = operation.get("target_type")
            target_id = operation.get("target_id")
            if not target_type or target_id is None:
                continue
            updated_at = await self._resolve_entity_updated_at(
                db,
                entity_type=str(target_type),
                entity_id=uuid.UUID(str(target_id)),
            )
            if updated_at is not None:
                entities[(str(target_type), uuid.UUID(str(target_id)))] = updated_at

        return {
            "entity_versions": [
                {
                    "entity_type": entity_type,
                    "entity_id": str(entity_id),
                    "updated_at": updated_at.isoformat(),
                }
                for (entity_type, entity_id), updated_at in sorted(
                    entities.items(),
                    key=lambda item: (item[0][0], str(item[0][1])),
                )
            ],
            "context_fingerprint": context_assembler.context_fingerprint(context_data),
        }

    async def _assert_run_plan_freshness(self, db: AsyncSession, *, run: AgentRun) -> None:
        meta = run.meta or {}
        raw_expiry = meta.get("plan_expires_at")
        if isinstance(raw_expiry, str):
            try:
                plan_expires_at = datetime.fromisoformat(raw_expiry)
            except ValueError:
                plan_expires_at = None
            else:
                if plan_expires_at is not None and plan_expires_at <= datetime.now(UTC):
                    raise BadRequestException(
                        "计划已过期，请重新生成后再确认。",
                        details={"code": "plan_expired"},
                    )

        raw_plan_basis = meta.get("plan_basis")
        if not isinstance(raw_plan_basis, dict):
            return
        entity_versions = cast(list[dict[str, Any]], raw_plan_basis.get("entity_versions", []))
        for entity_version in entity_versions:
            try:
                entity_id = uuid.UUID(str(entity_version["entity_id"]))
                expected_updated_at = datetime.fromisoformat(str(entity_version["updated_at"]))
            except (KeyError, ValueError):
                continue
            current_updated_at = await self._resolve_entity_updated_at(
                db,
                entity_type=str(entity_version["entity_type"]),
                entity_id=entity_id,
            )
            if current_updated_at is None or current_updated_at != expected_updated_at:
                raise BadRequestException(
                    "计划依赖的对象已变化，请重新生成后再确认。",
                    details={
                        "code": "stale_plan",
                        "entity_type": entity_version.get("entity_type"),
                        "entity_id": str(entity_id),
                    },
                )

        project = await project_service.get(db, id=run.project_id)
        latest_checkpoint = await self.checkpoint_store.latest_by_thread(db, thread_id=run.thread_id)
        user_message = None
        if run.user_message_id is not None:
            try:
                user_message = await self.message_store.get(db, run.user_message_id)
            except NotFoundException:
                user_message = None
        request_context = cast(dict[str, Any], meta.get("request_context", {}))
        current_context = await context_assembler.build_context(
            db,
            project=project,
            request_context={**request_context, "_user_message": user_message.content if user_message is not None else ""},
            user_message=user_message.content if user_message is not None else "",
            latest_checkpoint=latest_checkpoint,
            mode="planning",
        )
        current_fingerprint = context_assembler.context_fingerprint(current_context)
        expected_fingerprint = str(raw_plan_basis.get("context_fingerprint") or "")
        if expected_fingerprint and current_fingerprint != expected_fingerprint:
            raise BadRequestException(
                "工作区上下文已漂移，请重新生成计划后再确认。",
                details={"code": "workspace_drift_detected"},
            )

    async def _resolve_entity_updated_at(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> datetime | None:
        if entity_type == "project":
            return (await project_service.get(db, id=entity_id)).updated_at
        if entity_type == "character":
            return (await character_service.get(db, id=entity_id)).updated_at
        if entity_type == "world_setting":
            return (await world_setting_service.get(db, id=entity_id)).updated_at
        if entity_type == "volume":
            return (await volume_service.get(db, id=entity_id)).updated_at
        if entity_type == "chapter":
            return (await chapter_service.get(db, id=entity_id)).updated_at
        if entity_type == "scene":
            return (await scene_service.get(db, id=entity_id)).updated_at
        return None

    def _plan_precheck_from_operations(self, operations: list[dict[str, Any]]) -> dict[str, Any]:
        for operation in operations:
            execution_result = cast(dict[str, Any], operation.get("execution_result") or {})
            run_precheck = execution_result.get("run_precheck")
            if isinstance(run_precheck, dict):
                return run_precheck
        return {
            "status": "pass",
            "summary": "计划级连续性预检通过。",
            "warnings": [],
            "facts_used": [],
        }

    async def _normalize_operation_payload(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        request_context: dict[str, Any],
        operation: PlannedOperationSpec,
    ) -> dict[str, Any]:
        tool_name = operation.tool_name
        payload = dict(operation.payload)
        target_type: str | None = None
        target_id: uuid.UUID | None = None
        target_display: str | None = None
        preview_content_hash: str | None = None
        preview: OperationPreview

        if tool_name == "update_project_outline":
            project = await self._resolve_project(
                db,
                project_id=project_id,
                payload=payload,
                request_context=request_context,
            )
            updates = await self._filter_project_outline_update_payload(cast(dict[str, Any], payload.get("updates", payload)))
            merged = self._merge_preview_data(project, updates)
            preview_content_hash = _hash_text(cast(str | None, merged.get("story_outline")))
            preview = OperationPreview(
                changed_fields=list(updates.keys()),
                before_summary=self._project_summary(project),
                after_summary=self._project_summary_data(merged),
                diff=_build_diff(project.story_outline, cast(str | None, updates.get("story_outline"))),
                reason=operation.reason,
            )
            normalized_payload = {"project_id": str(project.id), "updates": updates}
            target_type = "project"
            target_id = project.id
            target_display = project.name

        elif tool_name == "create_character":
            normalized_payload = self._filter_character_create_payload(payload)
            preview = OperationPreview(
                changed_fields=list(normalized_payload.keys()),
                before_summary="将创建新人物",
                after_summary=f"{normalized_payload['name']} / {normalized_payload.get('role') or '未设定角色'}",
                reason=operation.reason,
            )
            target_type = "character"
            target_display = cast(str, normalized_payload["name"])

        elif tool_name == "update_character":
            character = await self._resolve_character(db, project_id=project_id, payload=payload, request_context=request_context)
            updates = self._filter_character_update_payload(cast(dict[str, Any], payload.get("updates", {})))
            if not updates:
                raise BadRequestException("update_character requires a non-empty updates object")
            merged = self._merge_preview_data(character, updates)
            preview = OperationPreview(
                changed_fields=list(updates.keys()),
                before_summary=self._character_summary(character),
                after_summary=self._character_summary_data(merged),
                diff=_build_diff(character.notes, cast(str | None, updates.get("notes"))),
                reason=operation.reason,
            )
            normalized_payload = {"character_id": str(character.id), "updates": updates}
            target_type = "character"
            target_id = character.id
            target_display = character.name

        elif tool_name == "create_world_setting":
            normalized_payload = self._filter_world_setting_create_payload(payload)
            preview_content_hash = _hash_text(cast(str | None, normalized_payload.get("content")))
            preview = OperationPreview(
                changed_fields=list(normalized_payload.keys()),
                before_summary="将创建新设定",
                after_summary=self._world_setting_summary_data(normalized_payload),
                diff=_build_diff(None, cast(str | None, normalized_payload.get("content"))),
                reason=operation.reason,
            )
            target_type = "world_setting"
            target_display = cast(str, normalized_payload["name"])

        elif tool_name == "update_world_setting":
            setting = await self._resolve_world_setting(
                db,
                project_id=project_id,
                payload=payload,
                request_context=request_context,
            )
            updates = self._filter_world_setting_update_payload(cast(dict[str, Any], payload.get("updates", {})))
            if not updates:
                raise BadRequestException("update_world_setting requires a non-empty updates object")
            merged = self._merge_preview_data(setting, updates)
            preview_content_hash = _hash_text(cast(str | None, merged.get("content")))
            preview = OperationPreview(
                changed_fields=list(updates.keys()),
                before_summary=self._world_setting_summary(setting),
                after_summary=self._world_setting_summary_data(merged),
                diff=_build_diff(setting.content, cast(str | None, updates.get("content"))),
                reason=operation.reason,
            )
            normalized_payload = {"setting_id": str(setting.id), "updates": updates}
            target_type = "world_setting"
            target_id = setting.id
            target_display = setting.name

        elif tool_name == "create_volume":
            normalized_payload = await self._filter_volume_create_payload(
                db,
                project_id=project_id,
                payload=payload,
            )
            preview = OperationPreview(
                changed_fields=list(normalized_payload.keys()),
                before_summary="将创建新卷细纲",
                after_summary=self._volume_summary_data(normalized_payload),
                diff=_build_diff(None, cast(str | None, normalized_payload.get("outline"))),
                reason=operation.reason,
            )
            target_type = "volume"
            target_display = f"第{normalized_payload['volume_number']}卷"

        elif tool_name == "update_volume":
            volume = await self._resolve_volume(
                db,
                project_id=project_id,
                payload=payload,
                request_context=request_context,
            )
            updates = self._filter_volume_update_payload(cast(dict[str, Any], payload.get("updates", {})))
            if not updates:
                raise BadRequestException("update_volume requires a non-empty updates object")
            merged = self._merge_preview_data(volume, updates)
            preview = OperationPreview(
                changed_fields=list(updates.keys()),
                before_summary=self._volume_summary(volume),
                after_summary=self._volume_summary_data(merged),
                diff=_build_diff(volume.outline, cast(str | None, updates.get("outline"))),
                reason=operation.reason,
            )
            normalized_payload = {"volume_id": str(volume.id), "updates": updates}
            target_type = "volume"
            target_id = volume.id
            target_display = f"第{volume.volume_number or '?'}卷 {volume.title or ''}".strip()

        elif tool_name == "create_chapter":
            normalized_payload = await self._filter_chapter_create_payload(db, project_id=project_id, payload=payload)
            preview_content_hash = _hash_text(cast(str | None, normalized_payload.get("content")))
            preview = OperationPreview(
                changed_fields=list(normalized_payload.keys()),
                before_summary="将创建新章节",
                after_summary=self._chapter_summary_data(normalized_payload),
                diff=_build_diff(None, cast(str | None, normalized_payload.get("content"))),
                reason=operation.reason,
            )
            target_type = "chapter"
            target_display = f"第{normalized_payload['chapter_number']}章"

        elif tool_name == "update_chapter":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            updates = self._filter_chapter_update_payload(cast(dict[str, Any], payload.get("updates", {})))
            if not updates:
                raise BadRequestException("update_chapter requires a non-empty updates object")
            merged = self._merge_preview_data(chapter, updates)
            preview_content_hash = _hash_text(cast(str | None, merged.get("content")))
            preview = OperationPreview(
                changed_fields=list(updates.keys()),
                before_summary=self._chapter_summary(chapter),
                after_summary=self._chapter_summary_data(merged),
                diff=_build_diff(chapter.content, cast(str | None, updates.get("content"))),
                reason=operation.reason,
            )
            normalized_payload = {"chapter_id": str(chapter.id), "updates": updates}
            target_type = "chapter"
            target_id = chapter.id
            target_display = f"第{chapter.chapter_number}章 {chapter.title or ''}".strip()

        elif tool_name == "write_chapter_content":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            content = str(payload.get("content", "")).strip()
            mode = str(payload.get("mode", "replace"))
            normalized_payload = {
                "chapter_id": str(chapter.id),
                "mode": mode,
                "content": content,
            }
            if not normalized_payload["content"]:
                raise BadRequestException("write_chapter_content requires content")
            next_content = self._apply_text_mode(chapter.content, content, mode)
            preview_content_hash = _hash_text(next_content)
            preview = OperationPreview(
                changed_fields=["content"],
                before_summary=_excerpt(chapter.content),
                after_summary=_excerpt(next_content),
                diff=_build_diff(chapter.content, next_content),
                reason=operation.reason,
            )
            target_type = "chapter"
            target_id = chapter.id
            target_display = f"第{chapter.chapter_number}章 {chapter.title or ''}".strip()

        elif tool_name == "create_scene":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            normalized_payload = await self._filter_scene_create_payload(
                db,
                project_id=project_id,
                chapter=chapter,
                payload=payload,
            )
            preview_content_hash = _hash_text(cast(str | None, normalized_payload.get("content")))
            preview = OperationPreview(
                changed_fields=list(normalized_payload.keys()),
                before_summary=f"将在第{chapter.chapter_number}章创建新场景",
                after_summary=self._scene_summary_data(normalized_payload),
                diff=_build_diff(None, cast(str | None, normalized_payload.get("content"))),
                reason=operation.reason,
            )
            target_type = "scene"
            target_display = f"第{chapter.chapter_number}章 / 场景 {normalized_payload['scene_order']}"

        elif tool_name == "update_scene":
            scene = await self._resolve_scene(db, project_id=project_id, payload=payload, request_context=request_context)
            updates = await self._filter_scene_update_payload(db, project_id=project_id, payload=cast(dict[str, Any], payload.get("updates", {})))
            if not updates:
                raise BadRequestException("update_scene requires a non-empty updates object")
            merged = self._merge_preview_data(scene, updates)
            preview_content_hash = _hash_text(cast(str | None, merged.get("content")))
            preview = OperationPreview(
                changed_fields=list(updates.keys()),
                before_summary=self._scene_summary(scene),
                after_summary=self._scene_summary_data(merged),
                diff=_build_diff(scene.content, cast(str | None, updates.get("content"))),
                reason=operation.reason,
            )
            normalized_payload = {"scene_id": str(scene.id), "updates": updates}
            target_type = "scene"
            target_id = scene.id
            target_display = f"场景 {scene.scene_order}"

        elif tool_name == "write_scene_content":
            scene = await self._resolve_scene(db, project_id=project_id, payload=payload, request_context=request_context)
            content = str(payload.get("content", "")).strip()
            mode = str(payload.get("mode", "replace"))
            normalized_payload = {
                "scene_id": str(scene.id),
                "mode": mode,
                "content": content,
            }
            if not normalized_payload["content"]:
                raise BadRequestException("write_scene_content requires content")
            next_content = self._apply_text_mode(scene.content, content, mode)
            preview_content_hash = _hash_text(next_content)
            preview = OperationPreview(
                changed_fields=["content"],
                before_summary=_excerpt(scene.content),
                after_summary=_excerpt(next_content),
                diff=_build_diff(scene.content, next_content),
                reason=operation.reason,
            )
            target_type = "scene"
            target_id = scene.id
            target_display = f"场景 {scene.scene_order}"

        else:
            raise BadRequestException(f"Unsupported tool '{tool_name}'")

        return {
            "tool_name": tool_name,
            "description": operation.description,
            "reason": operation.reason,
            "payload": normalized_payload,
            "preview": preview.model_dump(),
            "target_type": target_type,
            "target_id": target_id,
            "target_display": target_display,
            "preview_content_hash": preview_content_hash,
        }

    async def _execute_operation(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        request_context: dict[str, Any],
        operation: AgentOperation,
    ) -> None:
        tool_name = operation.tool_name
        payload = dict(operation.payload)

        if tool_name == "update_project_outline":
            project = await self._resolve_project(
                db,
                project_id=project_id,
                payload=payload,
                request_context=request_context,
            )
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="project",
                target_id=project.id,
                data=_serialize_model(project),
                stage="pre_update",
            )
            updated_project = await project_service.update(
                db,
                db_obj=project,
                obj_in=ProjectUpdate(**cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_project.id
            operation.target_display = updated_project.name
            execution_result = dict(operation.execution_result or {})
            execution_result["updated_id"] = str(updated_project.id)
            operation.execution_result = execution_result

        elif tool_name == "create_character":
            character_in = CharacterCreate(project_id=project_id, **payload)
            character = await character_service.create_with_project(db, obj_in=character_in, project_id=project_id)
            operation.target_id = character.id
            operation.target_display = character.name
            operation.execution_result = {"created_id": str(character.id)}
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="character",
                target_id=character.id,
                data=_serialize_model(character),
                stage="post_create",
            )

        elif tool_name == "update_character":
            character = await self._resolve_character(db, project_id=project_id, payload=payload, request_context=request_context)
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="character",
                target_id=character.id,
                data=_serialize_model(character),
                stage="pre_update",
            )
            updated_character = await character_service.update(
                db,
                db_obj=character,
                obj_in=CharacterUpdate(**cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_character.id
            operation.target_display = updated_character.name
            execution_result = dict(operation.execution_result or {})
            execution_result["updated_id"] = str(updated_character.id)
            operation.execution_result = execution_result

        elif tool_name == "create_world_setting":
            world_setting_in = WorldSettingCreate(project_id=project_id, **payload)
            setting = await world_setting_service.create_with_project(db, obj_in=world_setting_in, project_id=project_id)
            operation.target_id = setting.id
            operation.target_display = setting.name
            operation.execution_result = {"created_id": str(setting.id)}
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="world_setting",
                target_id=setting.id,
                data=_serialize_model(setting),
                stage="post_create",
            )

        elif tool_name == "update_world_setting":
            setting = await self._resolve_world_setting(db, project_id=project_id, payload=payload, request_context=request_context)
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="world_setting",
                target_id=setting.id,
                data=_serialize_model(setting),
                stage="pre_update",
            )
            updated_setting = await world_setting_service.update(
                db,
                db_obj=setting,
                obj_in=WorldSettingUpdate(**cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_setting.id
            operation.target_display = updated_setting.name
            execution_result = dict(operation.execution_result or {})
            execution_result["updated_id"] = str(updated_setting.id)
            operation.execution_result = execution_result

        elif tool_name == "create_volume":
            volume_in = VolumeCreate(project_id=project_id, **payload)
            volume = await volume_service.create_with_project(db, obj_in=volume_in, project_id=project_id)
            operation.target_id = volume.id
            operation.target_display = f"第{volume.volume_number or '?'}卷 {volume.title or ''}".strip()
            operation.execution_result = {"created_id": str(volume.id)}
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="volume",
                target_id=volume.id,
                data=_serialize_model(volume),
                stage="post_create",
            )

        elif tool_name == "update_volume":
            volume = await self._resolve_volume(
                db,
                project_id=project_id,
                payload=payload,
                request_context=request_context,
            )
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="volume",
                target_id=volume.id,
                data=_serialize_model(volume),
                stage="pre_update",
            )
            updated_volume = await volume_service.update(
                db,
                db_obj=volume,
                obj_in=VolumeUpdate(**cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_volume.id
            operation.target_display = f"第{updated_volume.volume_number or '?'}卷 {updated_volume.title or ''}".strip()
            execution_result = dict(operation.execution_result or {})
            execution_result["updated_id"] = str(updated_volume.id)
            operation.execution_result = execution_result

        elif tool_name == "create_chapter":
            chapter_in = ChapterCreate(project_id=project_id, **payload)
            chapter = await chapter_service.create_with_project(db, obj_in=chapter_in, project_id=project_id)
            operation.target_id = chapter.id
            operation.target_display = f"第{chapter.chapter_number}章 {chapter.title or ''}".strip()
            operation.execution_result = {"created_id": str(chapter.id)}
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="chapter",
                target_id=chapter.id,
                data=_serialize_model(chapter),
                stage="post_create",
            )

        elif tool_name == "update_chapter":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="chapter",
                target_id=chapter.id,
                data=_serialize_model(chapter),
                stage="pre_update",
            )
            updated_chapter = await chapter_service.update(
                db,
                db_obj=chapter,
                obj_in=ChapterUpdate.model_validate(cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_chapter.id
            operation.target_display = f"第{updated_chapter.chapter_number}章 {updated_chapter.title or ''}".strip()
            execution_result = dict(operation.execution_result or {})
            execution_result["updated_id"] = str(updated_chapter.id)
            operation.execution_result = execution_result

        elif tool_name == "write_chapter_content":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="chapter",
                target_id=chapter.id,
                data=_serialize_model(chapter),
                stage="pre_update",
            )
            next_content = self._apply_text_mode(chapter.content, str(payload["content"]), str(payload.get("mode", "replace")))
            updated_chapter = await chapter_service.update(
                db,
                db_obj=chapter,
                obj_in=ChapterUpdate.model_validate({"content": next_content}),
            )
            operation.target_id = updated_chapter.id
            operation.target_display = f"第{updated_chapter.chapter_number}章 {updated_chapter.title or ''}".strip()
            execution_result = dict(operation.execution_result or {})
            execution_result["updated_id"] = str(updated_chapter.id)
            operation.execution_result = execution_result

        elif tool_name == "create_scene":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            scene_payload = {key: value for key, value in payload.items() if key != "chapter_id"}
            scene_in = SceneCreate(**scene_payload, chapter_id=chapter.id)
            scene = await scene_service.create_with_chapter(db, obj_in=scene_in, chapter_id=chapter.id)
            operation.target_id = scene.id
            operation.target_display = f"场景 {scene.scene_order}"
            operation.execution_result = {"created_id": str(scene.id)}
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="scene",
                target_id=scene.id,
                data=_serialize_model(scene),
                stage="post_create",
            )

        elif tool_name == "update_scene":
            scene = await self._resolve_scene(db, project_id=project_id, payload=payload, request_context=request_context)
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="scene",
                target_id=scene.id,
                data=_serialize_model(scene),
                stage="pre_update",
            )
            updated_scene = await scene_service.update(
                db,
                db_obj=scene,
                obj_in=SceneUpdate.model_validate(cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_scene.id
            operation.target_display = f"场景 {updated_scene.scene_order}"
            execution_result = dict(operation.execution_result or {})
            execution_result["updated_id"] = str(updated_scene.id)
            operation.execution_result = execution_result

        elif tool_name == "write_scene_content":
            scene = await self._resolve_scene(db, project_id=project_id, payload=payload, request_context=request_context)
            await self._create_operation_snapshot(
                db,
                project_id=project_id,
                operation=operation,
                target_type="scene",
                target_id=scene.id,
                data=_serialize_model(scene),
                stage="pre_update",
            )
            next_content = self._apply_text_mode(scene.content, str(payload["content"]), str(payload.get("mode", "replace")))
            updated_scene = await scene_service.update(
                db,
                db_obj=scene,
                obj_in=SceneUpdate.model_validate({"content": next_content}),
            )
            operation.target_id = updated_scene.id
            operation.target_display = f"场景 {updated_scene.scene_order}"
            execution_result = dict(operation.execution_result or {})
            execution_result["updated_id"] = str(updated_scene.id)
            operation.execution_result = execution_result

        else:
            raise BadRequestException(f"Unsupported tool '{tool_name}'")

        operation.status = AgentOperationStatus.EXECUTED.value
        await db.flush()

    async def _resolve_character(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
        request_context: dict[str, Any],
    ) -> Character:
        character_id = payload.get("character_id") or request_context.get("character_id")
        if character_id:
            return await character_service.get(db, id=uuid.UUID(str(character_id)))
        character_name = payload.get("character_name") or request_context.get("character_name")
        if character_name:
            result = await db.execute(
                select(Character)
                .where(Character.project_id == project_id, Character.name == str(character_name))
                .limit(1)
            )
            character = result.scalar_one_or_none()
            if character is not None:
                return character
        raise NotFoundException("Character target could not be resolved")

    async def _resolve_world_setting(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
        request_context: dict[str, Any],
    ) -> WorldSetting:
        setting_id = payload.get("setting_id") or request_context.get("setting_id")
        if setting_id:
            return await world_setting_service.get(db, id=uuid.UUID(str(setting_id)))
        setting_name = payload.get("setting_name") or request_context.get("setting_name")
        if setting_name:
            result = await db.execute(
                select(WorldSetting)
                .where(WorldSetting.project_id == project_id, WorldSetting.name == str(setting_name))
                .limit(1)
            )
            setting = result.scalar_one_or_none()
            if setting is not None:
                return setting
        raise NotFoundException("World setting target could not be resolved")

    async def _resolve_project(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
        request_context: dict[str, Any],
    ) -> Project:
        resolved_project_id = (
            payload.get("project_id")
            or request_context.get("project_id")
            or str(project_id)
        )
        project = await project_service.get(db, id=uuid.UUID(str(resolved_project_id)))
        if project.id != project_id:
            raise NotFoundException("Project target does not belong to the active workspace")
        return project

    async def _resolve_volume(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
        request_context: dict[str, Any],
    ) -> Volume:
        volume_id = payload.get("volume_id") or request_context.get("volume_id")
        if volume_id:
            resolved_volume = await volume_service.get(db, id=uuid.UUID(str(volume_id)))
            if resolved_volume.project_id != project_id:
                raise NotFoundException("Volume target does not belong to the active workspace")
            return resolved_volume

        volume_number = payload.get("volume_number") or request_context.get("volume_number")
        if volume_number is not None:
            matched_volume = await volume_service.get_by_volume_number(
                db,
                project_id=project_id,
                volume_number=int(volume_number),
            )
            if matched_volume is not None:
                return matched_volume

        volume_title = payload.get("volume_title") or payload.get("title") or request_context.get("volume_title")
        if volume_title:
            result = await db.execute(
                select(Volume)
                .where(Volume.project_id == project_id, Volume.title == str(volume_title))
                .limit(1)
            )
            titled_volume = result.scalar_one_or_none()
            if titled_volume is not None:
                return titled_volume
        raise NotFoundException("Volume target could not be resolved")

    async def _resolve_chapter(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
        request_context: dict[str, Any],
    ) -> Chapter:
        chapter_id = payload.get("chapter_id") or request_context.get("chapter_id")
        if chapter_id:
            return await chapter_service.get(db, id=uuid.UUID(str(chapter_id)))
        chapter_number = payload.get("chapter_number") or request_context.get("chapter_number")
        if chapter_number is not None:
            result = await db.execute(
                select(Chapter)
                .where(Chapter.project_id == project_id, Chapter.chapter_number == int(chapter_number))
                .limit(1)
            )
            chapter = result.scalar_one_or_none()
            if chapter is not None:
                return chapter
        raise NotFoundException("Chapter target could not be resolved")

    async def _resolve_scene(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
        request_context: dict[str, Any],
    ) -> Scene:
        scene_id = payload.get("scene_id") or request_context.get("scene_id")
        if scene_id:
            return await scene_service.get(db, id=uuid.UUID(str(scene_id)))

        chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
        scene_order = payload.get("scene_order") or request_context.get("scene_order")
        if scene_order is not None:
            result = await db.execute(
                select(Scene)
                .where(Scene.chapter_id == chapter.id, Scene.scene_order == int(scene_order))
                .limit(1)
            )
            scene = result.scalar_one_or_none()
            if scene is not None:
                return scene
        raise NotFoundException("Scene target could not be resolved")

    def _filter_character_create_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not str(payload.get("name", "")).strip():
            raise BadRequestException("create_character requires name")
        normalized = {
            "name": str(payload["name"]).strip(),
            "role": payload.get("role"),
            "profile": cast(dict[str, Any], payload.get("profile", {})),
            "relationships": cast(dict[str, Any], payload.get("relationships", {})),
            "arc_state": cast(dict[str, Any], payload.get("arc_state", {})),
            "notes": payload.get("notes"),
        }
        self._validate_schema(CharacterCreate, project_id=uuid.uuid4(), **normalized)
        return normalized

    def _filter_character_update_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise BadRequestException("update_character updates must be an object")
        updates: dict[str, Any] = {}
        for key in ["name", "role", "profile", "relationships", "arc_state", "notes"]:
            if key in payload:
                updates[key] = payload[key]
        self._validate_schema(CharacterUpdate, **updates)
        return updates

    VALID_CATEGORY_VALUES = frozenset({
        "magic_system",
        "geography",
        "history",
        "organization",
        "technology",
        "culture",
        "religion",
        "economy",
        "rules",
        "other",
    })

    CATEGORY_ALIASES: dict[str, str] = {
        "rule": "rules",
        "rules": "rules",
        "rulebook": "rules",
        "law": "rules",
        "lawbook": "rules",
        "magic": "magic_system",
        "magicsystem": "magic_system",
        "spell": "magic_system",
        "spell_system": "magic_system",
        "geo": "geography",
        "geographic": "geography",
        "location": "geography",
        "map": "geography",
        "hist": "history",
        "historical": "history",
        "past": "history",
        "org": "organization",
        "organizations": "organization",
        "group": "organization",
        "faction": "organization",
        "tech": "technology",
        "technologies": "technology",
        "cult": "culture",
        "cultures": "culture",
        "tradition": "culture",
        "relig": "religion",
        "religions": "religion",
        "faith": "religion",
        "god": "religion",
        "deity": "religion",
        "econom": "economy",
        "economics": "economy",
        "financial": "economy",
        "trade": "economy",
    }

    def _normalize_category(self, category: str) -> str:
        normalized = category.lower().strip()
        if normalized in self.VALID_CATEGORY_VALUES:
            return normalized
        return self.CATEGORY_ALIASES.get(normalized, "other")

    def _filter_world_setting_create_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_category = str(payload.get("category") or "other")
        normalized_category = self._normalize_category(raw_category)
        normalized = {
            "name": str(payload.get("name", "")).strip(),
            "category": normalized_category,
            "content": payload.get("content"),
            "meta": cast(dict[str, Any], payload.get("meta", {})),
        }
        self._validate_schema(WorldSettingCreate, project_id=uuid.uuid4(), **normalized)
        return normalized

    def _filter_world_setting_update_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise BadRequestException("update_world_setting updates must be an object")
        updates: dict[str, Any] = {}
        for key in ["name", "category", "content", "meta"]:
            if key in payload:
                value = payload[key]
                if key == "category" and value is not None:
                    value = self._normalize_category(str(value))
                updates[key] = value
        self._validate_schema(WorldSettingUpdate, **updates)
        return updates

    async def _filter_project_outline_update_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise BadRequestException("update_project_outline updates must be an object")
        story_outline = str(
            payload.get("story_outline")
            or payload.get("outline")
            or payload.get("content")
            or ""
        ).strip()
        if not story_outline:
            raise BadRequestException("update_project_outline requires a non-empty story_outline")
        updates = {"story_outline": story_outline}
        self._validate_schema(ProjectUpdate, **updates)
        return updates

    async def _filter_volume_create_payload(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        volume_number = payload.get("volume_number")
        if volume_number is None:
            volume_number = await volume_service.next_volume_number(db, project_id=project_id)
        normalized = {
            "volume_number": int(volume_number),
            "title": payload.get("title") or f"第{int(volume_number)}卷",
            "outline": payload.get("outline"),
            "notes": payload.get("notes"),
        }
        self._validate_schema(VolumeCreate, project_id=uuid.uuid4(), **normalized)
        return normalized

    def _filter_volume_update_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise BadRequestException("update_volume updates must be an object")
        updates: dict[str, Any] = {}
        for key in ["volume_number", "title", "outline", "notes"]:
            if key in payload:
                updates[key] = payload[key]
        self._validate_schema(VolumeUpdate, **updates)
        return updates

    async def _filter_chapter_create_payload(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        effective_volume_id = payload.get("volume_id")
        if effective_volume_id is None:
            project_volumes = await volume_service.get_by_project(db, project_id=project_id, limit=1)
            if project_volumes:
                effective_volume_id = str(project_volumes[0].id)
        chapter_number = payload.get("chapter_number")
        if chapter_number is None:
            if effective_volume_id is not None:
                chapters = await chapter_service.get_by_volume(db, volume_id=uuid.UUID(str(effective_volume_id)), limit=200)
            else:
                chapters = await chapter_service.get_by_project(db, project_id=project_id, limit=200)
            chapter_number = max((chapter.chapter_number for chapter in chapters), default=0) + 1
        normalized = {
            "chapter_number": int(chapter_number),
            "title": payload.get("title"),
            "outline": payload.get("outline"),
            "content": payload.get("content"),
            "status": payload.get("status", "draft"),
            "notes": payload.get("notes"),
            "volume_id": effective_volume_id,
        }
        self._validate_schema(ChapterCreate, project_id=uuid.uuid4(), **normalized)
        return normalized

    def _filter_chapter_update_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise BadRequestException("update_chapter updates must be an object")
        updates: dict[str, Any] = {}
        for key in ["chapter_number", "title", "outline", "content", "status", "notes", "volume_id"]:
            if key in payload:
                updates[key] = payload[key]
        self._validate_schema(ChapterUpdate, **updates)
        return updates

    async def _filter_scene_create_payload(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        chapter: Chapter,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        scene_order = payload.get("scene_order")
        if scene_order is None:
            scenes = await scene_service.get_by_chapter(db, chapter_id=chapter.id, limit=200)
            scene_order = max((scene.scene_order for scene in scenes), default=0) + 1

        pov_character_id = payload.get("pov_character_id")
        if pov_character_id is None and payload.get("pov_character_name"):
            character = await self._resolve_character(
                db,
                project_id=project_id,
                payload={"character_name": payload["pov_character_name"]},
                request_context={},
            )
            pov_character_id = str(character.id)

        normalized = {
            "chapter_id": str(chapter.id),
            "scene_order": int(scene_order),
            "pov_character_id": pov_character_id,
            "location": payload.get("location"),
            "content": payload.get("content"),
            "meta": cast(dict[str, Any], payload.get("meta", {})),
        }
        self._validate_schema(SceneCreate, **normalized)
        return normalized

    async def _filter_scene_update_payload(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise BadRequestException("update_scene updates must be an object")
        updates = dict(payload)
        if updates.get("pov_character_id") is None and updates.get("pov_character_name"):
            character = await self._resolve_character(
                db,
                project_id=project_id,
                payload={"character_name": updates["pov_character_name"]},
                request_context={},
            )
            updates["pov_character_id"] = str(character.id)
        updates.pop("pov_character_name", None)
        self._validate_schema(SceneUpdate, **updates)
        return updates

    def _apply_text_mode(self, existing: str | None, incoming: str, mode: str) -> str:
        if mode == "append" and existing:
            return f"{existing.rstrip()}\n\n{incoming.strip()}".strip()
        return incoming.strip()

    def _character_summary(self, character: Character) -> str:
        return self._character_summary_data(_serialize_model(character))

    def _character_summary_data(self, data: dict[str, Any]) -> str:
        return f"{data.get('name') or '未命名人物'} / {data.get('role') or '未设定角色'}"

    def _world_setting_summary(self, setting: WorldSetting) -> str:
        return self._world_setting_summary_data(_serialize_model(setting))

    def _world_setting_summary_data(self, data: dict[str, Any]) -> str:
        return f"{data.get('name') or '未命名设定'} / {data.get('category') or 'other'} / {_excerpt(cast(str | None, data.get('content')))}"

    def _project_summary(self, project: Project) -> str:
        return self._project_summary_data(_serialize_model(project))

    def _project_summary_data(self, data: dict[str, Any]) -> str:
        title = data.get("name") or "未命名项目"
        outline = cast(str | None, data.get("story_outline") or data.get("summary"))
        return f"{title} / {_excerpt(outline)}"

    def _volume_summary(self, volume: Volume) -> str:
        return self._volume_summary_data(_serialize_model(volume))

    def _volume_summary_data(self, data: dict[str, Any]) -> str:
        number = data.get("volume_number") or "?"
        title = data.get("title") or "未命名卷"
        outline = cast(str | None, data.get("outline"))
        return f"第{number}卷 {title} / {_excerpt(outline)}"

    def _chapter_summary(self, chapter: Chapter) -> str:
        return self._chapter_summary_data(_serialize_model(chapter))

    def _chapter_summary_data(self, data: dict[str, Any]) -> str:
        title = data.get("title") or "无标题"
        return f"第{data.get('chapter_number')}章 {title} / {_excerpt(cast(str | None, data.get('content') or data.get('outline')))}"

    def _scene_summary(self, scene: Scene) -> str:
        return self._scene_summary_data(_serialize_model(scene))

    def _scene_summary_data(self, data: dict[str, Any]) -> str:
        location = data.get("location") or "未设定地点"
        return f"场景 {data.get('scene_order')} / {location} / {_excerpt(cast(str | None, data.get('content')))}"

    def _merge_preview_data(self, model: Any, updates: dict[str, Any]) -> dict[str, Any]:
        merged = _serialize_model(model)
        for key, value in updates.items():
            merged[key] = _json_ready(value)
        return merged

    def _execution_warning(self, operations: list[AgentOperation]) -> str | None:
        write_tools = {"write_chapter_content", "write_scene_content", "update_world_setting", "update_character"}
        if any(operation.tool_name in write_tools for operation in operations):
            return "本次执行已完成持久化，并已尝试刷新记忆与依赖。"
        return None

    def _merge_warning_messages(self, base: str | None, warnings: list[str]) -> str | None:
        parts = [base] if base else []
        parts.extend(warning for warning in warnings if warning)
        if not parts:
            return None
        return "；".join(dict.fromkeys(parts))

    async def _refresh_operation_artifacts(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        request_context: dict[str, Any],
        operation: AgentOperation,
    ) -> str | None:
        if operation.tool_name not in {
            "create_chapter",
            "create_scene",
            "write_chapter_content",
            "write_scene_content",
            "create_character",
            "update_character",
            "create_world_setting",
            "update_world_setting",
        }:
            return None
        try:
            target = await self._load_operation_target(db, project_id=project_id, operation=operation)
            if operation.tool_name in {"create_character", "update_character"} and isinstance(target, Character):
                await self._refresh_character_memory(db, project_id=project_id, character=target)
                return None
            if operation.tool_name in {"create_world_setting", "update_world_setting"} and isinstance(target, WorldSetting):
                await self._refresh_world_setting_memory(db, project_id=project_id, setting=target)
                return None
            if operation.tool_name in PROSE_OPERATION_TOOLS and isinstance(target, (Chapter, Scene)):
                await self._refresh_prose_artifacts(
                    db,
                    project_id=project_id,
                    request_context=request_context,
                    operation=operation,
                    target=target,
                )
            return None
        except Exception as exc:
            logger.warning("Artifact refresh failed for operation %s: %s", operation.id, exc)
            execution_result = dict(operation.execution_result or {})
            execution_result["artifact_refresh"] = {
                "status": "failed",
                "message": str(exc),
            }
            operation.execution_result = execution_result
            await db.flush()
            return f"步骤 {operation.position} 的记忆/依赖刷新失败：{exc}"

    async def _refresh_character_memory(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        character: Character,
    ) -> None:
        content = (
            f"{character.name} / {character.role or '未设定角色'} / "
            f"{_excerpt(json.dumps(character.profile or {}, ensure_ascii=False), length=220) or '暂无详细档案'}"
        )
        embedding = await self._safe_embed_text(content)
        await memory_service.upsert_fact(
            db,
            project_id=project_id,
            memory_type="semantic",
            content=content,
            meta={
                "fact_kind": "character_profile",
                "character_ids": [str(character.id)],
                "source_type": "character",
                "source_id": str(character.id),
            },
            embedding=embedding,
        )

    async def _refresh_world_setting_memory(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        setting: WorldSetting,
    ) -> None:
        content = f"{setting.name} / {setting.category} / {_excerpt(setting.content, length=240) or '暂无内容'}"
        embedding = await self._safe_embed_text(content)
        await memory_service.upsert_fact(
            db,
            project_id=project_id,
            memory_type="semantic",
            content=content,
            meta={
                "fact_kind": "world_setting",
                "world_setting_ids": [str(setting.id)],
                "source_type": "world_setting",
                "source_id": str(setting.id),
            },
            embedding=embedding,
        )

    async def _refresh_prose_artifacts(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        request_context: dict[str, Any],
        operation: AgentOperation,
        target: Chapter | Scene,
    ) -> None:
        raw_content = self._target_content(target)
        if not raw_content or not raw_content.strip():
            return
        content = raw_content
        project = await project_service.get(db, id=project_id)
        context_data = await context_assembler.build_context(
            db,
            project=project,
            request_context={**request_context, "_user_message": content[:120]},
            user_message=content[:120],
            latest_checkpoint=None,
            mode="artifact_refresh",
        )
        refresh_payload = await self._extract_artifact_refresh_payload(
            operation=operation,
            content=content,
            context_data=context_data,
        )
        await self._persist_prose_memories_and_dependencies(
            db,
            project_id=project_id,
            operation=operation,
            target=target,
            refresh_payload=refresh_payload,
            content=content,
        )

    async def _extract_artifact_refresh_payload(
        self,
        *,
        operation: AgentOperation,
        content: str,
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = dedent(
            f"""
            你是小说知识整理器。请根据正文整理 episode 和 facts。
            始终返回 JSON：
            {{
              "episode_summary": "一段中文事件摘要",
              "timeline_marker": "可选，时间锚点",
              "character_names": ["..."],
              "world_setting_names": ["..."],
              "facts": [
                {{
                  "content": "具体事实",
                  "fact_kind": "event|rule|relationship|character_state|setting_detail",
                  "timeline_marker": "可选",
                  "character_names": ["..."],
                  "world_setting_names": ["..."]
                }}
              ]
            }}

            相关对象清单：
            {json.dumps({
                "characters": context_data.get("characters", []),
                "world_settings": context_data.get("world_settings", []),
            }, ensure_ascii=False)}

            当前步骤：
            {json.dumps({
                "tool_name": operation.tool_name,
                "target_type": operation.target_type,
                "target_display": operation.target_display,
            }, ensure_ascii=False)}

            正文：
            {content}
            """
        ).strip()
        result = await self.llm.generate(
            [
                {"role": "system", "content": "你是严谨的小说知识整理器。始终返回 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=700,
        )
        parsed = _extract_json_object(result["content"])
        facts = [
            fact
            for fact in cast(list[dict[str, Any]], parsed.get("facts", []))
            if isinstance(fact, dict) and str(fact.get("content", "")).strip()
        ]
        return {
            "episode_summary": str(parsed.get("episode_summary") or _excerpt(content, length=200) or "正文事件摘要"),
            "timeline_marker": str(parsed.get("timeline_marker") or "").strip() or None,
            "character_names": [str(item) for item in cast(list[Any], parsed.get("character_names", [])) if str(item).strip()],
            "world_setting_names": [
                str(item) for item in cast(list[Any], parsed.get("world_setting_names", [])) if str(item).strip()
            ],
            "facts": facts[:5],
        }

    async def _persist_prose_memories_and_dependencies(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        operation: AgentOperation,
        target: Chapter | Scene,
        refresh_payload: dict[str, Any],
        content: str,
    ) -> None:
        source_type = "chapter" if isinstance(target, Chapter) else "scene"
        source_id = target.id
        project_characters = await character_service.get_by_project(db, project_id=project_id, limit=300)
        project_settings = await world_setting_service.get_by_project(db, project_id=project_id, limit=300)
        matched_character_ids = self._match_object_ids_by_name(
            names=cast(list[str], refresh_payload.get("character_names", [])),
            objects=project_characters,
        )
        matched_world_setting_ids = self._match_object_ids_by_name(
            names=cast(list[str], refresh_payload.get("world_setting_names", [])),
            objects=project_settings,
        )

        episode_meta = {
            "fact_kind": "episode_summary",
            "character_ids": matched_character_ids,
            "world_setting_ids": matched_world_setting_ids,
            "chapter_id": str(target.id) if isinstance(target, Chapter) else str(target.chapter_id),
            "scene_id": str(target.id) if isinstance(target, Scene) else None,
            "timeline_marker": refresh_payload.get("timeline_marker"),
            "source_type": source_type,
            "source_id": str(source_id),
        }
        if isinstance(target, Chapter) and target.volume_id is not None:
            episode_meta["volume_id"] = str(target.volume_id)
        episode_embedding = await self._safe_embed_text(str(refresh_payload["episode_summary"]))
        await memory_service.upsert_fact(
            db,
            project_id=project_id,
            memory_type="episode",
            content=str(refresh_payload["episode_summary"]),
            meta=episode_meta,
            embedding=episode_embedding,
        )

        for fact in cast(list[dict[str, Any]], refresh_payload.get("facts", [])):
            fact_character_ids = self._match_object_ids_by_name(
                names=[str(item) for item in cast(list[Any], fact.get("character_names", [])) if str(item).strip()],
                objects=project_characters,
            )
            fact_setting_ids = self._match_object_ids_by_name(
                names=[str(item) for item in cast(list[Any], fact.get("world_setting_names", [])) if str(item).strip()],
                objects=project_settings,
            )
            fact_meta = {
                "fact_kind": str(fact.get("fact_kind") or "event"),
                "character_ids": fact_character_ids,
                "world_setting_ids": fact_setting_ids,
                "chapter_id": episode_meta.get("chapter_id"),
                "scene_id": episode_meta.get("scene_id"),
                "volume_id": episode_meta.get("volume_id"),
                "timeline_marker": fact.get("timeline_marker") or refresh_payload.get("timeline_marker"),
                "source_type": source_type,
                "source_id": str(source_id),
            }
            fact_embedding = await self._safe_embed_text(str(fact["content"]))
            await memory_service.upsert_fact(
                db,
                project_id=project_id,
                memory_type="fact",
                content=str(fact["content"]),
                meta=fact_meta,
                embedding=fact_embedding,
            )

        existing_dependencies = await dependency_service.get_by_source(
            db,
            project_id=project_id,
            source_type=source_type,
            source_id=source_id,
            limit=500,
        )
        for dependency in existing_dependencies:
            if dependency.target_type not in {"character", "world_setting"}:
                continue
            await db.delete(dependency)
        await db.flush()
        for character_id in matched_character_ids:
            await dependency_service.get_or_create(
                db,
                project_id=project_id,
                source_type=source_type,
                source_id=source_id,
                target_type="character",
                target_id=uuid.UUID(character_id),
                dependency_type="references",
            )
        for setting_id in matched_world_setting_ids:
            await dependency_service.get_or_create(
                db,
                project_id=project_id,
                source_type=source_type,
                source_id=source_id,
                target_type="world_setting",
                target_id=uuid.UUID(setting_id),
                dependency_type="references",
            )

        execution_result = dict(operation.execution_result or {})
        execution_result["artifact_refresh"] = {
            "status": "completed",
            "episode_summary": refresh_payload.get("episode_summary"),
            "fact_count": len(cast(list[Any], refresh_payload.get("facts", []))),
            "dependency_character_count": len(matched_character_ids),
            "dependency_world_setting_count": len(matched_world_setting_ids),
        }
        operation.execution_result = execution_result
        await db.flush()

    async def _safe_embed_text(self, text: str) -> list[float] | None:
        if not text.strip():
            return None
        try:
            return await self.llm.embed_single(text)
        except Exception:
            logger.debug("Embedding unavailable for artifact refresh text.")
            return None

    def _match_object_ids_by_name(self, *, names: list[str], objects: list[Any]) -> list[str]:
        normalized_names = {re.sub(r"\s+", "", name).strip().lower() for name in names if name.strip()}
        matched_ids: list[str] = []
        for obj in objects:
            obj_name = str(getattr(obj, "name", "") or "")
            if not obj_name:
                continue
            if re.sub(r"\s+", "", obj_name).strip().lower() not in normalized_names:
                continue
            matched_ids.append(str(obj.id))
        return matched_ids

    def _build_skill_snapshot(
        self,
        bundle: AgentSkillBundle,
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        tool_names = [str(operation["tool_name"]) for operation in operations]
        return {
            "profile_id": bundle.profile.id,
            "planner": {
                "name": bundle.planner.name,
                "source": str(bundle.planner.source_path),
            },
            "operations": [
                {
                    "tool_name": tool_name,
                    "skill_name": bundle.operations[tool_name].name,
                    "source": str(bundle.operations[tool_name].source_path),
                }
                for tool_name in tool_names
                if tool_name in bundle.operations
            ],
        }

    def _validate_schema(self, schema: type[BaseModel], **data: Any) -> None:
        try:
            schema(**data)
        except ValidationError as exc:
            raise BadRequestException(f"Invalid planner payload for {schema.__name__}: {exc}") from exc

    def _compact_policy_payload(self) -> dict[str, Any]:
        return {
            "policy_version": COMPACT_POLICY_VERSION,
            "message_threshold": COMPACTION_MESSAGE_THRESHOLD,
            "run_threshold": COMPACTION_RUN_THRESHOLD,
            "char_threshold": COMPACTION_CHAR_THRESHOLD,
            "recent_window_limit": RECENT_HISTORY_WINDOW_LIMIT,
            "checkpoint_delta_limit": CHECKPOINT_DELTA_HISTORY_LIMIT,
        }

    def _retained_window_payload(
        self,
        *,
        history: list[AgentMessage],
        history_mode: Literal["recent_window", "checkpoint_delta"],
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> dict[str, Any]:
        return {
            "history_mode": history_mode,
            "message_count": len(history),
            "character_count": sum(len(message.content) for message in history),
            "retained_message_limit": (
                CHECKPOINT_DELTA_HISTORY_LIMIT if history_mode == "checkpoint_delta" else RECENT_HISTORY_WINDOW_LIMIT
            ),
            "oldest_message_id": str(history[0].id) if history else None,
            "newest_message_id": str(history[-1].id) if history else None,
            "checkpoint_id": str(latest_checkpoint.id) if latest_checkpoint is not None else None,
            "compact_policy_version": COMPACT_POLICY_VERSION,
            "roles": list(dict.fromkeys(str(message.role) for message in history)),
        }

    def _focused_object_types_from_request_context(self, request_context: dict[str, Any]) -> list[str]:
        return [
            name
            for key, name in (
                ("project_id", "project"),
                ("character_id", "character"),
                ("world_setting_id", "world_setting"),
                ("volume_id", "volume"),
                ("chapter_id", "chapter"),
                ("scene_id", "scene"),
            )
            if request_context.get(key)
        ]

    def _active_bundle_contract_payload_for_checkpoint(
        self,
        *,
        request_context: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
        recent_runs: list[AgentRun],
    ) -> dict[str, Any]:
        return {
            "contract_version": ACTIVE_BUNDLE_CONTRACT_VERSION,
            "source": "checkpoint_snapshot",
            "included_sections": [
                "project",
                "request_context",
                "thread_summary",
                "recent_run_digest",
                "compact_policy",
                "compaction_boundary",
            ],
            "focused_object_types": self._focused_object_types_from_request_context(request_context),
            "checkpoint_id": str(latest_checkpoint.id) if latest_checkpoint is not None else None,
            "includes_thread_summary": True,
            "includes_recent_run_digest": bool(recent_runs),
            "collections": {
                "characters_count": 0,
                "characters_limit": CHARACTER_CONTEXT_LIMIT,
                "world_settings_count": 0,
                "world_settings_limit": WORLD_SETTING_CONTEXT_LIMIT,
                "volumes_count": 0,
                "volumes_limit": VOLUME_CONTEXT_LIMIT,
                "chapters_count": 0,
                "chapters_limit": CHAPTER_CONTEXT_LIMIT,
                "current_scenes_count": 0,
                "current_scenes_limit": SCENE_CONTEXT_LIMIT,
                "recent_run_digest_count": min(len(recent_runs), RECENT_RUN_DIGEST_LIMIT),
                "recent_run_digest_limit": RECENT_RUN_DIGEST_LIMIT,
            },
        }

    def _active_bundle_contract_payload_for_run(
        self,
        *,
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> dict[str, Any]:
        latest_checkpoint_data = cast(dict[str, Any], context_data.get("latest_checkpoint") or {})
        recent_run_digest = cast(dict[str, Any], latest_checkpoint_data.get("recent_run_digest") or {})
        current_scenes = cast(list[Any], context_data.get("current_scenes") or [])
        included_sections = sorted(
            key
            for key, value in context_data.items()
            if key not in {"planner_window", "retained_window", "active_bundle_contract"} and value not in (None, [], {})
        )
        focused_object_types = sorted(
            key.removeprefix("current_")
            for key, value in context_data.items()
            if key.startswith("current_") and value not in (None, [], {})
        )
        return {
            "contract_version": ACTIVE_BUNDLE_CONTRACT_VERSION,
            "source": "checkpoint_plus_live_context" if latest_checkpoint is not None else "live_context",
            "included_sections": included_sections,
            "focused_object_types": focused_object_types,
            "checkpoint_id": str(latest_checkpoint.id) if latest_checkpoint is not None else None,
            "includes_thread_summary": latest_checkpoint is not None,
            "includes_recent_run_digest": bool(recent_run_digest.get("runs")),
            "collections": {
                "characters_count": len(cast(list[Any], context_data.get("characters", []))),
                "characters_limit": CHARACTER_CONTEXT_LIMIT,
                "world_settings_count": len(cast(list[Any], context_data.get("world_settings", []))),
                "world_settings_limit": WORLD_SETTING_CONTEXT_LIMIT,
                "volumes_count": len(cast(list[Any], context_data.get("volumes", []))),
                "volumes_limit": VOLUME_CONTEXT_LIMIT,
                "chapters_count": len(cast(list[Any], context_data.get("chapters", []))),
                "chapters_limit": CHAPTER_CONTEXT_LIMIT,
                "current_scenes_count": len(current_scenes),
                "current_scenes_limit": SCENE_CONTEXT_LIMIT,
                "recent_run_digest_count": len(cast(list[Any], recent_run_digest.get("runs", []))),
                "recent_run_digest_limit": RECENT_RUN_DIGEST_LIMIT,
            },
        }

    async def _run_response(self, db: AsyncSession, run: AgentRun) -> AgentRunResponse:
        operations = await self.operation_store.list_by_run(db, run_id=run.id)
        subtasks = await self.subtask_store.list_by_run(db, run_id=run.id)
        meta = run.meta or {}
        return AgentRunResponse(
            id=run.id,
            thread_id=run.thread_id,
            project_id=run.project_id,
            user_message_id=run.user_message_id,
            assistant_message_id=run.assistant_message_id,
            revision_of_run_id=run.revision_of_run_id,
            status=cast(Any, run.status),
            summary=run.summary,
            error_message=run.error_message,
            warning_message=run.warning_message,
            verification_status=cast(Any, run.verification_status),
            verification_summary=run.verification_summary,
            execution_contract=self._execution_contract_response(meta),
            risk_summary=self._run_risk_summary_response(meta=meta, operations=operations),
            compact_policy=self._compact_policy_response(meta),
            planner_window=self._planner_window_response(meta),
            retained_window=self._retained_window_response(meta),
            active_bundle_contract=self._active_bundle_contract_response(meta),
            plan_expires_at=self._plan_expires_at_response(meta),
            plan_basis=self._plan_basis_response(meta),
            meta=meta,
            confirmed_at=run.confirmed_at,
            secondary_confirmed_at=run.secondary_confirmed_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
            operations=[self._operation_response(operation) for operation in operations],
            subtasks=[self._subtask_response(subtask) for subtask in subtasks],
        )

    def _run_risk_summary_response(
        self,
        *,
        meta: dict[str, Any],
        operations: list[AgentOperation],
    ) -> AgentRunRiskSummaryResponse | None:
        """Return the stored risk summary snapshot, with deterministic fallback for legacy runs."""
        raw = meta.get("risk_summary")
        if isinstance(raw, dict):
            try:
                return AgentRunRiskSummaryResponse.model_validate(raw)
            except ValidationError:
                logger.warning("Skipping invalid risk_summary payload during response serialization.")

        return agent_risk_service.build_run_risk_summary(
            operations,
            profile_id=str(meta.get("profile_id") or "default"),
        )

    def _compact_policy_response(self, meta: dict[str, Any]) -> AgentCompactPolicyResponse:
        raw = meta.get("compact_policy")
        if isinstance(raw, dict):
            try:
                return AgentCompactPolicyResponse.model_validate(raw)
            except ValidationError:
                logger.warning("Skipping invalid compact_policy payload during response serialization.")
        return AgentCompactPolicyResponse.model_validate(self._compact_policy_payload())

    def _planner_window_response(self, meta: dict[str, Any]) -> AgentPlannerWindowResponse | None:
        raw = meta.get("planner_window")
        if not isinstance(raw, dict):
            return None
        try:
            return AgentPlannerWindowResponse.model_validate(raw)
        except ValidationError:
            logger.warning("Skipping invalid planner_window payload during response serialization.")
            return None

    def _retained_window_response(self, meta: dict[str, Any]) -> AgentRetainedWindowResponse | None:
        raw = meta.get("retained_window")
        if not isinstance(raw, dict):
            return None
        try:
            return AgentRetainedWindowResponse.model_validate(raw)
        except ValidationError:
            logger.warning("Skipping invalid retained_window payload during response serialization.")
            return None

    def _plan_expires_at_response(self, meta: dict[str, Any]) -> datetime | None:
        raw = meta.get("plan_expires_at")
        if not isinstance(raw, str):
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            logger.warning("Skipping invalid plan_expires_at payload during response serialization.")
            return None

    def _plan_basis_response(self, meta: dict[str, Any]) -> AgentPlanBasisResponse | None:
        raw = meta.get("plan_basis")
        if not isinstance(raw, dict):
            return None
        try:
            return AgentPlanBasisResponse(
                entity_versions=[
                    AgentPlanBasisEntityVersionResponse(
                        entity_type=str(item["entity_type"]),
                        entity_id=uuid.UUID(str(item["entity_id"])),
                        updated_at=datetime.fromisoformat(str(item["updated_at"])),
                    )
                    for item in cast(list[dict[str, Any]], raw.get("entity_versions", []))
                ],
                context_fingerprint=str(raw["context_fingerprint"]),
            )
        except (ValidationError, KeyError, TypeError, ValueError):
            logger.warning("Skipping invalid plan_basis payload during response serialization.")
            return None

    def _active_bundle_contract_response(
        self,
        meta: dict[str, Any],
    ) -> AgentActiveBundleContractResponse | None:
        raw = meta.get("active_bundle_contract")
        if not isinstance(raw, dict):
            return None
        try:
            return AgentActiveBundleContractResponse.model_validate(raw)
        except ValidationError:
            logger.warning("Skipping invalid active_bundle_contract payload during response serialization.")
            return None

    def _thread_response(self, thread: AgentThread) -> AgentThreadResponse:
        return AgentThreadResponse.model_validate(thread)

    def _message_response(self, message: AgentMessage) -> AgentMessageResponse:
        return AgentMessageResponse.model_validate(message)

    def _operation_response(self, operation: AgentOperation) -> AgentOperationResponse:
        preview = OperationPreview.model_validate(operation.preview)
        return AgentOperationResponse(
            id=operation.id,
            run_id=operation.run_id,
            position=operation.position,
            tool_name=operation.tool_name,
            target_type=operation.target_type,
            target_id=operation.target_id,
            target_display=operation.target_display,
            description=operation.description,
            reason=operation.reason,
            payload=operation.payload,
            preview=preview,
            permission_level=cast(Any, operation.permission_level),
            risk_level=cast(Any, operation.risk_level),
            requires_secondary_confirmation=operation.requires_secondary_confirmation,
            status=cast(Any, operation.status),
            verification_status=cast(Any, operation.verification_status),
            verification_summary=operation.verification_summary,
            execution_result=operation.execution_result,
            error_message=operation.error_message,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )

    def _subtask_response(self, subtask: AgentSubtask) -> AgentSubtaskResponse:
        meta = subtask.meta or {}
        return AgentSubtaskResponse(
            id=subtask.id,
            run_id=subtask.run_id,
            position=subtask.position,
            role=cast(Any, subtask.role),
            title=subtask.title,
            status=cast(Any, subtask.status),
            summary=subtask.summary,
            error_message=subtask.error_message,
            child_trace=self._subtask_trace_response(meta),
            pipeline_steps=self._pipeline_steps_response(meta),
            meta=meta,
            created_at=subtask.created_at,
            updated_at=subtask.updated_at,
        )

    def _subtask_trace_response(self, meta: dict[str, Any]) -> AgentSubtaskTraceResponse | None:
        raw = meta.get("child_trace")
        if not isinstance(raw, dict):
            return None
        try:
            attempts = [
                AgentSubtaskAttemptResponse.model_validate(attempt)
                for attempt in cast(list[dict[str, Any]], raw.get("attempts", []))
            ]
            return AgentSubtaskTraceResponse(
                unit_id=str(raw["unit_id"]),
                role=cast(Any, raw["role"]),
                execution_phase=cast(Any, raw["execution_phase"]),
                retry_strategy=cast(Any, raw["retry_strategy"]),
                depends_on=[str(item) for item in cast(list[Any], raw.get("depends_on", []))],
                operation_positions=[int(item) for item in cast(list[Any], raw.get("operation_positions", []))],
                tool_scope=[str(item) for item in cast(list[Any], raw.get("tool_scope", []))],
                input_summary=cast(str | None, raw.get("input_summary")),
                output_summary=cast(str | None, raw.get("output_summary")),
                attempts=attempts,
            )
        except (ValidationError, KeyError, TypeError, ValueError):
            logger.warning("Skipping invalid child_trace payload during response serialization.")
            return None

    def _pipeline_steps_response(self, meta: dict[str, Any]) -> list[AgentPipelineStepResponse]:
        raw = meta.get("pipeline_steps")
        if not isinstance(raw, list):
            return []
        steps: list[AgentPipelineStepResponse] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                steps.append(AgentPipelineStepResponse.model_validate(item))
            except ValidationError:
                logger.warning("Skipping invalid pipeline step payload during response serialization.")
        return steps

    def _execution_contract_response(self, meta: dict[str, Any]) -> AgentExecutionContractResponse | None:
        raw = meta.get("permission_matrix")
        if not isinstance(raw, dict):
            return None
        try:
            phases = [
                AgentExecutionPhaseResponse(
                    phase=cast(Any, phase["phase"]),
                    mode=cast(Any, phase["mode"]),
                    allowed_permission_levels=[cast(Any, item) for item in cast(list[Any], phase.get("allowed_permission_levels", []))],
                    tool_scope=[str(item) for item in cast(list[Any], phase.get("tool_scope", []))],
                    role_scope=[cast(Any, item) for item in cast(list[Any], phase.get("role_scope", []))],
                    confirmation_gate=cast(Any, phase.get("confirmation_gate", "none")),
                    requires_confirmation=bool(phase.get("requires_confirmation", False)),
                    requires_secondary_confirmation=bool(phase.get("requires_secondary_confirmation", False)),
                    operation_count=int(phase.get("operation_count", 0)),
                    child_units=[
                        self._child_unit_response(child_unit)
                        for child_unit in cast(list[dict[str, Any]], phase.get("child_units", []))
                    ],
                    capabilities=[
                        self._capability_response(capability)
                        for capability in cast(list[dict[str, Any]], phase.get("capabilities", []))
                    ],
                )
                for phase in cast(list[dict[str, Any]], raw.get("phases", []))
            ]
            return AgentExecutionContractResponse(
                registry_version=str(raw.get("registry_version", CAPABILITY_REGISTRY_VERSION)),
                phases=phases,
            )
        except (ValidationError, KeyError, TypeError, ValueError):
            logger.warning("Skipping invalid execution contract payload during response serialization.")
            return None

    def _child_unit_response(
        self,
        child_unit: dict[str, Any],
    ) -> AgentExecutionChildUnitResponse:
        """Serialize one child unit contract from the execution matrix."""
        raw = child_unit
        return AgentExecutionChildUnitResponse(
            unit_id=str(raw["unit_id"]),
            role=cast(Any, raw["role"]),
            phase=cast(Any, raw["phase"]),
            stage=cast(Any, raw["stage"]),
            mode=cast(Any, raw["mode"]),
            title=str(raw["title"]),
            description=str(raw["description"]),
            tool_scope=[str(item) for item in cast(list[Any], raw.get("tool_scope", []))],
            capability_ids=[str(item) for item in cast(list[Any], raw.get("capability_ids", []))],
            depends_on=[str(item) for item in cast(list[Any], raw.get("depends_on", []))],
            operation_positions=[int(item) for item in cast(list[Any], raw.get("operation_positions", []))],
            confirmation_gate=cast(Any, raw.get("confirmation_gate", "none")),
            requires_confirmation=bool(raw.get("requires_confirmation", False)),
            internal_only=bool(raw.get("internal_only", True)),
        )

    def _capability_response(self, capability: CapabilityScopeSummary | dict[str, Any]) -> AgentCapabilityResponse:
        """Serialize one capability definition or run-scoped instance."""
        raw = capability if isinstance(capability, dict) else capability.model_dump(mode="json")
        policy = cast(dict[str, Any], raw["policy"])
        record = raw.get("execution_record")
        return AgentCapabilityResponse(
            capability_id=str(raw["capability_id"]),
            name=str(raw["name"]),
            kind=cast(Any, raw["kind"]),
            description=str(raw["description"]),
            tool_scope=[str(item) for item in cast(list[Any], raw.get("tool_scope", []))],
            policy=AgentCapabilityPolicyResponse(
                execution_phase=cast(Any, policy["execution_phase"]),
                source_role=cast(Any, policy["source_role"]),
                confirmation_gate=cast(Any, policy["confirmation_gate"]),
                internal_only=bool(policy.get("internal_only", True)),
                requires_confirmation=bool(policy.get("requires_confirmation", False)),
            ),
            execution_record=(
                AgentCapabilityExecutionRecordResponse(
                    record_id=str(record["record_id"]),
                    source_role=cast(Any, record["source_role"]),
                    status=cast(Any, record["status"]),
                    tool_scope=[str(item) for item in cast(list[Any], record.get("tool_scope", []))],
                    input_summary=cast(str | None, record.get("input_summary")),
                    output_summary=cast(str | None, record.get("output_summary")),
                    attempt_count=int(record.get("attempt_count", 1)),
                )
                if isinstance(record, dict)
                else None
            ),
        )

    def _checkpoint_response(
        self,
        checkpoint: AgentThreadCheckpoint,
    ) -> AgentThreadCheckpointResponse:
        active_object_bundle = checkpoint.active_object_bundle or {}
        compact_policy = active_object_bundle.get("compact_policy")
        compaction_boundary = active_object_bundle.get("compaction_boundary")
        active_bundle_contract = active_object_bundle.get("active_bundle_contract")
        if isinstance(active_bundle_contract, dict) and not active_bundle_contract.get("checkpoint_id"):
            active_bundle_contract = {**active_bundle_contract, "checkpoint_id": str(checkpoint.id)}
        return AgentThreadCheckpointResponse(
            id=checkpoint.id,
            thread_id=checkpoint.thread_id,
            profile_id=checkpoint.profile_id,
            thread_summary=checkpoint.thread_summary,
            active_object_bundle=active_object_bundle,
            recent_run_digest=checkpoint.recent_run_digest or {},
            source_message_count=checkpoint.source_message_count,
            source_run_count=checkpoint.source_run_count,
            total_context_characters=checkpoint.total_context_characters,
            compact_policy=(
                AgentCompactPolicyResponse.model_validate(compact_policy)
                if isinstance(compact_policy, dict)
                else AgentCompactPolicyResponse.model_validate(self._compact_policy_payload())
            ),
            compaction_boundary=(
                AgentCompactionBoundaryResponse.model_validate(compaction_boundary)
                if isinstance(compaction_boundary, dict)
                else None
            ),
            active_bundle_contract=(
                AgentActiveBundleContractResponse.model_validate(active_bundle_contract)
                if isinstance(active_bundle_contract, dict)
                else None
            ),
            created_at=checkpoint.created_at,
            updated_at=checkpoint.updated_at,
        )

    def _classify_operations(
        self,
        operations: list[dict[str, Any]],
        *,
        profile_id: str,
    ) -> list[dict[str, Any]]:
        """Attach permission and risk metadata to planner operations."""
        classified = agent_risk_service.classify_operations(operations, profile_id=profile_id)
        for operation in classified:
            operation["verification_status"] = AgentVerificationStatus.PENDING.value
        return classified

    def _build_subtasks(
        self,
        *,
        planner_output: PlannerOutput,
        operations: list[dict[str, Any]],
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> list[dict[str, Any]]:
        """Build validated internal subtask units with per-role recovery boundaries."""
        provided_by_role: dict[str, PlannedSubtaskSpec] = {
            str(subtask.role): subtask for subtask in planner_output.subtasks
        }

        synthesized_by_role: dict[str, PlannedSubtaskSpec] = {
            AgentSubtaskRole.PLANNER.value: self._execute_planner_unit(planner_output=planner_output),
            AgentSubtaskRole.RESEARCHER.value: self._execute_researcher_unit(
                context_data=context_data,
                latest_checkpoint=latest_checkpoint,
            ),
            AgentSubtaskRole.WRITER.value: self._execute_writer_unit(operations=operations),
            AgentSubtaskRole.EDITOR.value: self._execute_editor_unit(operations=operations),
            AgentSubtaskRole.CONTINUITY.value: self._execute_continuity_unit(operations=operations),
        }

        return [
            self._materialize_subtask_unit(
                role=role,
                provided=provided_by_role.get(role),
                synthesized=synthesized_by_role[role],
                operations=operations,
                context_data=context_data,
                latest_checkpoint=latest_checkpoint,
            ).model_dump()
            for role in (
                AgentSubtaskRole.PLANNER.value,
                AgentSubtaskRole.RESEARCHER.value,
                AgentSubtaskRole.WRITER.value,
                AgentSubtaskRole.EDITOR.value,
                AgentSubtaskRole.CONTINUITY.value,
            )
        ]

    def _execute_planner_unit(
        self,
        *,
        planner_output: PlannerOutput,
    ) -> PlannedSubtaskSpec:
        """Build the planner unit from the final user-visible plan."""
        return PlannedSubtaskSpec(
            role="planner",
            title="Planner blueprint",
            status="completed",
            summary=_excerpt(planner_output.summary or planner_output.assistant_message, length=SUBTASK_SUMMARY_LIMIT),
            meta={"depends_on": []},
        )

    def _execute_researcher_unit(
        self,
        *,
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> PlannedSubtaskSpec:
        """Build the researcher unit from resolved project context."""
        current_objects = [
            f"{key}:{value['id']}"
            for key, value in context_data.items()
            if key.startswith("current_") and isinstance(value, dict) and value.get("id")
        ]
        summary = (
            f"已装配项目上下文，人物 {len(cast(list[Any], context_data.get('characters', [])))} / "
            f"设定 {len(cast(list[Any], context_data.get('world_settings', [])))} / "
            f"卷 {len(cast(list[Any], context_data.get('volumes', [])))} / "
            f"章节 {len(cast(list[Any], context_data.get('chapters', [])))}。"
        )
        if current_objects:
            summary += f" 当前聚焦：{', '.join(current_objects)}。"
        if latest_checkpoint is not None:
            summary += f" 已参考 checkpoint {latest_checkpoint.id}。"
        return PlannedSubtaskSpec(
            role="researcher",
            title="Context bundle",
            status="completed",
            summary=_excerpt(summary, length=SUBTASK_SUMMARY_LIMIT),
            meta={"depends_on": ["planner"]},
        )

    def _execute_writer_unit(
        self,
        *,
        operations: list[dict[str, Any]],
    ) -> PlannedSubtaskSpec:
        """Build the writer unit for prose-candidate generation."""
        writer_tools = {
            "write_chapter_content",
            "write_scene_content",
            "create_chapter",
            "create_scene",
        }
        writer_ops = [
            operation
            for operation in operations
            if operation["tool_name"] in writer_tools and self._operation_content_candidate(operation)
        ]
        pipeline_steps = [
            step
            for operation in writer_ops
            for step in cast(
                list[dict[str, Any]],
                cast(dict[str, Any], operation.get("execution_result") or {}).get("planning_pipeline", []),
            )
        ]
        return PlannedSubtaskSpec(
            role="writer",
            title="Writer candidate",
            status="completed" if writer_ops else "skipped",
            summary=_excerpt(
                f"生成 {len(writer_ops)} 个正文候选，全部在 planning 阶段完成。"
                if writer_ops
                else "本轮无需生成正文候选。",
                length=SUBTASK_SUMMARY_LIMIT,
            ),
            meta={
                "depends_on": ["planner", "researcher"],
                "operation_positions": [int(operation["position"]) for operation in writer_ops if "position" in operation],
                "pipeline_steps": pipeline_steps,
            },
        )

    def _execute_editor_unit(
        self,
        *,
        operations: list[dict[str, Any]],
    ) -> PlannedSubtaskSpec:
        """Build the editor unit for structured metadata and patch edits."""
        editor_ops = [
            operation
            for operation in operations
            if operation["tool_name"] in {
                "update_project_outline",
                "update_character",
                "update_world_setting",
                "create_volume",
                "update_volume",
                "update_chapter",
                "update_scene",
            }
        ]
        return PlannedSubtaskSpec(
            role="editor",
            title="Editor diff",
            status="completed" if editor_ops else "skipped",
            summary=_excerpt(
                f"整理 {len(editor_ops)} 个结构化修改步骤。"
                if editor_ops
                else "本轮无需结构化 patch/diff。",
                length=SUBTASK_SUMMARY_LIMIT,
            ),
            meta={
                "depends_on": ["planner", "researcher"],
                "operation_positions": [int(operation["position"]) for operation in editor_ops if "position" in operation],
            },
        )

    def _execute_continuity_unit(
        self,
        *,
        operations: list[dict[str, Any]],
    ) -> PlannedSubtaskSpec:
        """Build the continuity unit before the execution-time gate runs."""
        run_precheck = self._plan_precheck_from_operations(operations)
        relevant_targets = [
            f"{operation.get('target_type') or 'unknown'}:{operation.get('target_display') or operation.get('target_id') or operation['tool_name']}"
            for operation in operations
        ]
        pipeline_steps = [
            step
            for operation in operations
            for step in cast(
                list[dict[str, Any]],
                cast(dict[str, Any], operation.get("execution_result") or {}).get("planning_pipeline", []),
            )
            if str(step.get("stage")) == "continuity_precheck"
        ]
        return PlannedSubtaskSpec(
            role="continuity",
            title="Continuity gate",
            status="failed" if str(run_precheck.get("status")) == "block" else "completed",
            summary=_excerpt(
                f"{run_precheck.get('summary') or '执行前将验证目标对象、写入一致性与多步修改冲突。'}"
                + (f" 本轮涉及：{', '.join(relevant_targets[:4])}。" if relevant_targets else ""),
                length=SUBTASK_SUMMARY_LIMIT,
            ),
            error_message=str(run_precheck.get("summary")) if str(run_precheck.get("status")) == "block" else None,
            meta={
                "depends_on": ["planner", "researcher", "writer", "editor"],
                "pipeline_steps": pipeline_steps,
                "precheck": run_precheck,
            },
        )

    def _materialize_subtask_unit(
        self,
        *,
        role: str,
        provided: PlannedSubtaskSpec | None,
        synthesized: PlannedSubtaskSpec,
        operations: list[dict[str, Any]],
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> SubtaskExecutionResult:
        """Validate one subtask unit and recover to the service-generated fallback when needed."""
        max_attempts = 2 if provided is not None else 1
        retryable = provided is not None
        chosen = provided or synthesized
        attempt_count = 1
        source = "planner" if provided is not None else "service"
        validation_error = self._validate_subtask_candidate(
            role=role,
            candidate=chosen,
            operations=operations,
        )
        initial_validation_error = validation_error

        if validation_error is not None and provided is not None:
            chosen = synthesized
            attempt_count = 2
            source = "service_recovery"
            validation_error = self._validate_subtask_candidate(
                role=role,
                candidate=chosen,
                operations=operations,
            )

        validation_status = "passed"
        validation_summary = "Subtask passed validation."
        status = chosen.status
        error_message = chosen.error_message
        summary = _excerpt(chosen.summary, length=SUBTASK_SUMMARY_LIMIT)
        if source == "service_recovery":
            validation_status = "recovered"
            validation_summary = "Planner-provided subtask was invalid; recovered to service-generated fallback."
        if validation_error is not None:
            validation_status = "failed"
            validation_summary = validation_error
            status = "failed"
            error_message = validation_error
            summary = summary or validation_error

        next_meta = dict(chosen.meta or {})
        child_trace = self._build_subtask_execution_trace(
            role=role,
            source=source,
            max_attempts=max_attempts,
            validation_status=validation_status,
            validation_summary=validation_summary,
            initial_validation_error=initial_validation_error,
            chosen=chosen,
            operations=operations,
            context_data=context_data,
            latest_checkpoint=latest_checkpoint,
            summary=summary,
        )
        next_meta.update(
            {
                "unit": role,
                "source": source,
                "attempt_count": attempt_count,
                "max_attempts": max_attempts,
                "retryable": retryable,
                "validation_status": validation_status,
                "validation_summary": validation_summary,
                "retry_strategy": child_trace.retry_strategy,
                "child_trace": child_trace.model_dump(),
            }
        )

        return SubtaskExecutionResult(
            role=cast(Any, role),
            title=chosen.title,
            status=cast(Any, status),
            summary=summary,
            error_message=error_message,
            meta=next_meta,
        )

    def _build_subtask_execution_trace(
        self,
        *,
        role: str,
        source: str,
        max_attempts: int,
        validation_status: str,
        validation_summary: str,
        initial_validation_error: str | None,
        chosen: PlannedSubtaskSpec,
        operations: list[dict[str, Any]],
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
        summary: str | None,
    ) -> SubtaskExecutionTrace:
        """Build an observable child execution trace for one internal unit."""
        depends_on = [str(item) for item in cast(list[Any], chosen.meta.get("depends_on", []))]
        operation_positions = [
            int(position)
            for position in cast(list[Any], chosen.meta.get("operation_positions", []))
            if isinstance(position, int)
        ]
        retry_strategy: Literal["service_only", "planner_then_service_fallback"] = (
            "planner_then_service_fallback" if max_attempts > 1 else "service_only"
        )
        attempts: list[SubtaskExecutionAttempt] = []

        if source == "service_recovery":
            attempts.append(
                SubtaskExecutionAttempt(
                    attempt_number=1,
                    source="planner",
                    accepted=False,
                    validation_status="failed",
                    summary=initial_validation_error or "Planner-provided subtask failed validation.",
                )
            )
            attempts.append(
                SubtaskExecutionAttempt(
                    attempt_number=2,
                    source="service_recovery",
                    accepted=validation_status != "failed",
                    validation_status=cast(Any, validation_status),
                    summary=validation_summary,
                )
            )
        else:
            attempts.append(
                SubtaskExecutionAttempt(
                    attempt_number=1,
                    source=source,
                    accepted=validation_status != "failed",
                    validation_status=cast(Any, validation_status),
                    summary=validation_summary,
                )
            )

        return SubtaskExecutionTrace(
            unit_id=f"{role}-{uuid.uuid4().hex[:10]}",
            role=cast(Any, role),
            execution_phase="build_validation" if role == AgentSubtaskRole.CONTINUITY.value else "plan",
            retry_strategy=retry_strategy,
            depends_on=depends_on,
            operation_positions=operation_positions,
            tool_scope=self._subtask_tool_scope(role=role),
            input_summary=self._build_subtask_input_summary(
                role=role,
                operations=operations,
                context_data=context_data,
                latest_checkpoint=latest_checkpoint,
                operation_positions=operation_positions,
            ),
            output_summary=summary,
            attempts=attempts,
        )

    def _subtask_tool_scope(self, *, role: str) -> list[str]:
        """Return the internal tool scope for one child unit."""
        if role == AgentSubtaskRole.RESEARCHER.value:
            return list(INTERNAL_READ_SEARCH_TOOLS)
        if role == AgentSubtaskRole.PLANNER.value:
            return ["compose_run_blueprint", "classify_operation_risk"]
        if role == AgentSubtaskRole.WRITER.value:
            return ["draft_prose_candidate", "stage_content_preview"]
        if role == AgentSubtaskRole.EDITOR.value:
            return ["build_structured_diff", "stage_patch_preview"]
        return ["verify_preview_consistency", "check_target_resolution", "detect_multi_step_conflict"]

    def _capability_registry(self) -> dict[str, CapabilityScopeSummary]:
        """Return the stable workflow capability registry."""
        return {
            "project_inventory": CapabilityScopeSummary(
                capability_id="project_inventory",
                name="Project Inventory",
                kind="read_search",
                description="读取项目大纲、卷细纲、人物、设定、章节与场景的当前清单。",
                tool_scope=[
                    "resolve_current_project",
                    "list_project_characters",
                    "list_project_world_settings",
                    "list_project_volumes",
                    "list_project_chapters",
                    "list_project_scenes",
                ],
                policy=CapabilityPolicySummary(
                    execution_phase="plan",
                    source_role=AgentSubtaskRole.RESEARCHER.value,
                    confirmation_gate="none",
                    internal_only=True,
                    requires_confirmation=False,
                ),
            ),
            "focused_object_resolution": CapabilityScopeSummary(
                capability_id="focused_object_resolution",
                name="Focused Object Resolution",
                kind="read_search",
                description="根据当前请求解析聚焦对象，命中项目、人物、设定、卷、章节或场景。",
                tool_scope=[
                    "resolve_current_project",
                    "resolve_current_character",
                    "resolve_current_world_setting",
                    "resolve_current_volume",
                    "resolve_current_chapter",
                    "resolve_current_scene",
                ],
                policy=CapabilityPolicySummary(
                    execution_phase="plan",
                    source_role=AgentSubtaskRole.RESEARCHER.value,
                    confirmation_gate="none",
                    internal_only=True,
                    requires_confirmation=False,
                ),
            ),
            "checkpoint_context": CapabilityScopeSummary(
                capability_id="checkpoint_context",
                name="Checkpoint Context",
                kind="read_search",
                description="读取最近线程 checkpoint，为长期线程提供压缩上下文。",
                tool_scope=["load_latest_checkpoint"],
                policy=CapabilityPolicySummary(
                    execution_phase="plan",
                    source_role=AgentSubtaskRole.RESEARCHER.value,
                    confirmation_gate="none",
                    internal_only=True,
                    requires_confirmation=False,
                ),
            ),
            "operation_execution": CapabilityScopeSummary(
                capability_id="operation_execution",
                name="Operation Execution",
                kind="planning",
                description="按已确认的 operation 执行项目对象写入。",
                tool_scope=[],
                policy=CapabilityPolicySummary(
                    execution_phase="build",
                    source_role="executor",
                    confirmation_gate="single",
                    internal_only=True,
                    requires_confirmation=True,
                ),
            ),
        }

    def _instantiate_capability(
        self,
        *,
        registry: dict[str, CapabilityScopeSummary],
        capability_id: str,
        execution_record: CapabilityExecutionRecordSummary | None = None,
        tool_scope: list[str] | None = None,
        confirmation_gate: Literal["none", "single", "double"] | None = None,
    ) -> CapabilityScopeSummary:
        """Create one run-scoped capability instance from the registry."""
        base = registry[capability_id]
        return CapabilityScopeSummary(
            capability_id=base.capability_id,
            name=base.name,
            kind=base.kind,
            description=base.description,
            tool_scope=list(tool_scope or base.tool_scope),
            policy=CapabilityPolicySummary(
                execution_phase=base.policy.execution_phase,
                source_role=base.policy.source_role,
                confirmation_gate=confirmation_gate or base.policy.confirmation_gate,
                internal_only=base.policy.internal_only,
                requires_confirmation=base.policy.requires_confirmation,
            ),
            execution_record=execution_record,
        )

    def _read_search_capabilities(
        self,
        *,
        registry: dict[str, CapabilityScopeSummary],
        subtasks: list[dict[str, Any]],
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> list[CapabilityScopeSummary]:
        """Split the researcher read/search layer into stable internal capabilities."""
        role_scope = {str(subtask["role"]) for subtask in subtasks}
        if AgentSubtaskRole.RESEARCHER.value not in role_scope:
            return []
        current_targets = sorted(
            key.removeprefix("current_")
            for key, value in context_data.items()
            if key.startswith("current_") and isinstance(value, dict) and value.get("id")
        )
        inventory_tools = [
            "resolve_current_project",
            "list_project_characters",
            "list_project_world_settings",
            "list_project_volumes",
            "list_project_chapters",
            "list_project_scenes",
        ]
        resolution_tools = [
            "resolve_current_project",
            "resolve_current_character",
            "resolve_current_world_setting",
            "resolve_current_volume",
            "resolve_current_chapter",
            "resolve_current_scene",
        ]
        return [
            self._instantiate_capability(
                registry=registry,
                capability_id="project_inventory",
                tool_scope=inventory_tools,
                execution_record=CapabilityExecutionRecordSummary(
                    record_id=f"cap-{uuid.uuid4().hex[:10]}",
                    source_role=AgentSubtaskRole.RESEARCHER.value,
                    status="completed",
                    tool_scope=inventory_tools,
                    input_summary="读取项目范围对象清单。",
                    output_summary=(
                        f"项目纲 1 / 人物 {len(cast(list[Any], context_data.get('characters', [])))} / "
                        f"设定 {len(cast(list[Any], context_data.get('world_settings', [])))} / "
                        f"卷 {len(cast(list[Any], context_data.get('volumes', [])))} / "
                        f"章节 {len(cast(list[Any], context_data.get('chapters', [])))}。"
                    ),
                ),
            ),
            self._instantiate_capability(
                registry=registry,
                capability_id="focused_object_resolution",
                tool_scope=resolution_tools,
                execution_record=CapabilityExecutionRecordSummary(
                    record_id=f"cap-{uuid.uuid4().hex[:10]}",
                    source_role=AgentSubtaskRole.RESEARCHER.value,
                    status="completed",
                    tool_scope=resolution_tools,
                    input_summary="根据当前请求尝试命中聚焦对象。",
                    output_summary=(
                        f"命中对象：{', '.join(current_targets)}。"
                        if current_targets
                        else "当前请求没有命中具体项目、卷、人物、设定、章节或场景。"
                    ),
                ),
            ),
            self._instantiate_capability(
                registry=registry,
                capability_id="checkpoint_context",
                tool_scope=["load_latest_checkpoint"],
                execution_record=CapabilityExecutionRecordSummary(
                    record_id=f"cap-{uuid.uuid4().hex[:10]}",
                    source_role=AgentSubtaskRole.RESEARCHER.value,
                    status="completed" if latest_checkpoint is not None else "skipped",
                    tool_scope=["load_latest_checkpoint"],
                    input_summary="读取最近一次线程压缩摘要。",
                    output_summary=(
                        f"已加载 checkpoint {latest_checkpoint.id}。"
                        if latest_checkpoint is not None
                        else "当前线程没有可复用的 checkpoint。"
                    ),
                ),
            ),
        ]

    def _build_execution_contract_payload(
        self,
        *,
        operations: list[dict[str, Any]],
        subtasks: list[dict[str, Any]],
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> dict[str, Any]:
        """Build the serialized execution contract payload for one run."""
        registry = self._capability_registry()
        plan_capabilities = self._read_search_capabilities(
            registry=registry,
            subtasks=subtasks,
            context_data=context_data,
            latest_checkpoint=latest_checkpoint,
        )
        build_capabilities = (
            [
                self._instantiate_capability(
                    registry=registry,
                    capability_id="operation_execution",
                    tool_scope=[str(operation["tool_name"]) for operation in operations],
                    confirmation_gate=(
                        "double"
                        if any(
                            str(operation["permission_level"]) == AgentPermissionLevel.HIGH_RISK_WRITE.value
                            for operation in operations
                        )
                        else "single"
                    ),
                    execution_record=CapabilityExecutionRecordSummary(
                        record_id=f"cap-{uuid.uuid4().hex[:10]}",
                        source_role="executor",
                        status="planned",
                        tool_scope=[str(operation["tool_name"]) for operation in operations],
                        input_summary=f"等待执行 {len(operations)} 个已确认 operation。",
                        output_summary="尚未进入执行阶段。",
                    ),
                )
            ]
            if operations
            else []
        )
        return agent_contract_service.build_execution_contract_payload(
            operations=operations,
            subtasks=subtasks,
            plan_capabilities=[capability.model_dump(mode="json") for capability in plan_capabilities],
            build_capabilities=[capability.model_dump(mode="json") for capability in build_capabilities],
            registry_version=CAPABILITY_REGISTRY_VERSION,
            internal_read_search_tools=list(INTERNAL_READ_SEARCH_TOOLS),
        )

    def _build_subtask_input_summary(
        self,
        *,
        role: str,
        operations: list[dict[str, Any]],
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
        operation_positions: list[int],
    ) -> str:
        """Summarize the resolved input contract for one child unit."""
        if role == AgentSubtaskRole.PLANNER.value:
            return f"基于 {len(operations)} 个待执行 operation 构建用户可见蓝图。"
        if role == AgentSubtaskRole.RESEARCHER.value:
            summary = (
                f"上下文包含人物 {len(cast(list[Any], context_data.get('characters', [])))} / "
                f"设定 {len(cast(list[Any], context_data.get('world_settings', [])))} / "
                f"章节 {len(cast(list[Any], context_data.get('chapters', [])))}。"
            )
            if latest_checkpoint is not None:
                summary += " 已加载最近 checkpoint。"
            return summary
        if role == AgentSubtaskRole.WRITER.value:
            return (
                f"为正文候选准备 {len(operation_positions)} 个写作型 operation，"
                f"位置 {operation_positions or ['none']}。"
            )
        if role == AgentSubtaskRole.EDITOR.value:
            return (
                f"为结构化 patch 准备 {len(operation_positions)} 个编辑型 operation，"
                f"位置 {operation_positions or ['none']}。"
            )
        return f"对 {len(operations)} 个 operation 执行最终一致性与写入前检查。"

    def _validate_subtask_candidate(
        self,
        *,
        role: str,
        candidate: PlannedSubtaskSpec,
        operations: list[dict[str, Any]],
    ) -> str | None:
        """Validate a single role-specific subtask candidate."""
        if not candidate.title.strip():
            return f"{role} subtask is missing title"

        writer_required_tools = {"write_chapter_content", "write_scene_content", "create_chapter", "create_scene"}
        writer_required = any(
            operation["tool_name"] in writer_required_tools and self._operation_content_candidate(operation)
            for operation in operations
        )
        editor_required = any(
            operation["tool_name"] in {
                "update_project_outline",
                "update_character",
                "update_world_setting",
                "create_volume",
                "update_volume",
                "update_chapter",
                "update_scene",
            }
            for operation in operations
        )

        if role in {AgentSubtaskRole.PLANNER.value, AgentSubtaskRole.RESEARCHER.value} and not (candidate.summary or "").strip():
            return f"{role} subtask requires a non-empty summary"
        if role == AgentSubtaskRole.WRITER.value and writer_required and candidate.status == "skipped":
            return "writer subtask cannot be skipped when prose candidates exist"
        if role == AgentSubtaskRole.EDITOR.value and editor_required and candidate.status == "skipped":
            return "editor subtask cannot be skipped when structured edits exist"
        if role == AgentSubtaskRole.CONTINUITY.value and candidate.status == "failed" and not (candidate.error_message or "").strip():
            return "continuity subtask must explain blocking failures"
        return None

    def _build_pre_plan_hook(
        self,
        *,
        project: Project,
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
        history: list[AgentMessage],
        history_mode: Literal["recent_window", "checkpoint_delta"],
    ) -> HookTraceEntry:
        """Record the pre-plan hook that assembled project context and profile state."""
        focused_objects = sorted(
            key.removeprefix("current_")
            for key in context_data
            if key.startswith("current_")
        )
        summary = (
            f"已装配 profile={project.agent_profile_id} 的规划上下文，"
            f"人物 {len(cast(list[Any], context_data.get('characters', [])))} / "
            f"设定 {len(cast(list[Any], context_data.get('world_settings', [])))} / "
            f"卷 {len(cast(list[Any], context_data.get('volumes', [])))} / "
            f"章节 {len(cast(list[Any], context_data.get('chapters', [])))}。"
        )
        if focused_objects:
            summary += f" 聚焦对象：{', '.join(focused_objects)}。"
        if latest_checkpoint is not None:
            summary += " 已引入最近 checkpoint。"
        if history_mode == "checkpoint_delta":
            summary += " 规划历史已切换为 checkpoint 增量窗口。"
        return HookTraceEntry(
            hook_name="PrePlan",
            status="completed",
            summary=_excerpt(summary, length=SUBTASK_SUMMARY_LIMIT),
            meta={
                "profile_id": project.agent_profile_id,
                "history_mode": history_mode,
                "history_messages": len(history),
                "retained_message_limit": (
                    CHECKPOINT_DELTA_HISTORY_LIMIT if history_mode == "checkpoint_delta" else RECENT_HISTORY_WINDOW_LIMIT
                ),
                "compact_policy_version": COMPACT_POLICY_VERSION,
                "active_bundle_source": cast(
                    dict[str, Any],
                    context_data.get("active_bundle_contract") or {},
                ).get("source"),
                "focused_object_types": cast(
                    dict[str, Any],
                    context_data.get("active_bundle_contract") or {},
                ).get("focused_object_types", []),
                "checkpoint_id": str(latest_checkpoint.id) if latest_checkpoint is not None else None,
            },
        )

    def _validate_blueprint(
        self,
        *,
        operations: list[dict[str, Any]],
        subtasks: list[dict[str, Any]],
    ) -> HookTraceEntry:
        """Validate the internal blueprint before persisting a new run."""
        roles = [str(subtask["role"]) for subtask in subtasks]
        if len(roles) != len(set(roles)):
            raise BadRequestException("Blueprint contains duplicate subtask roles")
        if AgentSubtaskRole.PLANNER.value not in roles:
            raise BadRequestException("Blueprint is missing planner subtask")
        if AgentSubtaskRole.RESEARCHER.value not in roles:
            raise BadRequestException("Blueprint is missing researcher subtask")
        if AgentSubtaskRole.CONTINUITY.value not in roles:
            raise BadRequestException("Blueprint is missing continuity subtask")
        failed_roles = [
            str(subtask["role"])
            for subtask in subtasks
            if str(subtask.get("status")) == AgentSubtaskStatus.FAILED.value
        ]
        if failed_roles:
            raise BadRequestException(
                f"Blueprint contains failed subtask units: {', '.join(sorted(failed_roles))}"
            )

        writer_required_tools = {"write_chapter_content", "write_scene_content", "create_chapter", "create_scene"}
        writer_required = any(
            operation["tool_name"] in writer_required_tools and self._operation_content_candidate(operation)
            for operation in operations
        )
        editor_required = any(
            operation["tool_name"] in {
                "update_project_outline",
                "update_character",
                "update_world_setting",
                "create_volume",
                "update_volume",
                "update_chapter",
                "update_scene",
            }
            for operation in operations
        )
        subtask_by_role = {str(subtask["role"]): subtask for subtask in subtasks}
        recovered_roles = [
            str(subtask["role"])
            for subtask in subtasks
            if str(cast(dict[str, Any], subtask.get("meta", {})).get("validation_status")) == "recovered"
        ]
        validation_status_by_role = {
            str(subtask["role"]): str(
                cast(dict[str, Any], subtask.get("meta", {})).get("validation_status", "unknown")
            )
            for subtask in subtasks
        }
        if writer_required and subtask_by_role.get(AgentSubtaskRole.WRITER.value, {}).get("status") == "skipped":
            raise BadRequestException("Writer subtask cannot be skipped when content candidates exist")
        if editor_required and subtask_by_role.get(AgentSubtaskRole.EDITOR.value, {}).get("status") == "skipped":
            raise BadRequestException("Editor subtask cannot be skipped when structured edits exist")

        summary = f"Blueprint 校验通过：{len(operations)} 个 operation，角色 {', '.join(sorted(roles))}。"
        if recovered_roles:
            summary += f" 已回退角色：{', '.join(sorted(recovered_roles))}。"

        return HookTraceEntry(
            hook_name="SubagentStop",
            status="completed",
            summary=_excerpt(summary, length=SUBTASK_SUMMARY_LIMIT),
            meta={
                "operation_count": len(operations),
                "roles": sorted(roles),
                "recovered_roles": sorted(recovered_roles),
                "validation_status_by_role": validation_status_by_role,
            },
        )

    def _operation_content_candidate(self, operation: dict[str, Any]) -> str | None:
        """Return the full candidate content represented by an operation, if any."""
        tool_name = str(operation["tool_name"])
        payload = cast(dict[str, Any], operation.get("payload", {}))
        if tool_name in {"write_chapter_content", "write_scene_content"}:
            return cast(str | None, payload.get("content"))
        if tool_name in {"create_chapter", "create_scene", "create_world_setting"}:
            return cast(str | None, payload.get("content"))
        if tool_name in {"update_chapter", "update_scene", "update_world_setting"}:
            updates = cast(dict[str, Any], payload.get("updates", {}))
            return cast(str | None, updates.get("content"))
        return None

    def _summarize_thread(self, *, history: list[AgentMessage], recent_runs: list[AgentRun]) -> str:
        """Produce a deterministic compact summary for long-running threads."""
        history_bits = [
            f"{message.role}:{_excerpt(message.content, length=90)}"
            for message in history[-8:]
        ]
        run_bits = [
            f"{run.status}:{_excerpt(run.summary, length=72)}"
            for run in recent_runs[:5]
        ]
        pieces = []
        if history_bits:
            pieces.append("最近消息：" + " | ".join(bit for bit in history_bits if bit))
        if run_bits:
            pieces.append("最近 runs：" + " | ".join(bit for bit in run_bits if bit))
        return _excerpt("；".join(pieces) or "线程内容较短，暂无压缩摘要。", length=900) or "线程内容较短，暂无压缩摘要。"

    def _check_continuity_gate(self, operations: list[AgentOperation]) -> str:
        """Block obviously conflicting multi-step plans before execution."""
        content_targets: dict[tuple[str, str], list[str]] = {}
        for operation in operations:
            if operation.target_type and operation.target_id and operation.tool_name in {
                "update_chapter",
                "write_chapter_content",
                "update_scene",
                "write_scene_content",
            }:
                key = (operation.target_type, str(operation.target_id))
                content_targets.setdefault(key, []).append(operation.tool_name)

        for (target_type, target_id), tools in content_targets.items():
            if len(tools) > 1:
                return f"{target_type}:{target_id} 在同一 run 中存在多个正文修改步骤，需先合并计划。"
        return "通过"

    async def _verify_operation(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        operation: AgentOperation,
    ) -> None:
        """Verify that the persisted target matches the preview produced during planning."""
        target = await self._load_operation_target(db, project_id=project_id, operation=operation)
        preview = OperationPreview.model_validate(operation.preview)
        actual_summary = self._target_summary(target, operation.tool_name)
        actual_content = self._target_content(target)
        operation.persisted_content_hash = _hash_text(actual_content)
        matched_fields, mismatched_fields = self._verify_operation_fields(operation=operation, target=target)
        snapshot, snapshot_summary = await self._verify_operation_snapshot_linkage(
            db,
            project_id=project_id,
            operation=operation,
        )
        snapshot_semantics_ok = snapshot is not None
        snapshot_semantic_summary: str | None = None
        content_transition_ok = True
        content_transition_summary: str | None = None
        domain_semantics_ok = True
        domain_semantic_summary: str | None = None
        if snapshot is not None:
            snapshot_semantics_ok, snapshot_semantic_summary = self._verify_operation_snapshot_semantics(
                operation=operation,
                snapshot=snapshot,
                target=target,
            )
            content_transition_ok, content_transition_summary = self._verify_operation_content_transition(
                operation=operation,
                snapshot=snapshot,
                target=target,
            )
        domain_semantics_ok, domain_semantic_summary = await self._verify_operation_domain_semantics(
            db,
            project_id=project_id,
            operation=operation,
            target=target,
        )

        content_match = (
            operation.preview_content_hash is None
            or operation.preview_content_hash == operation.persisted_content_hash
        )
        summary_match = preview.after_summary is None or preview.after_summary == actual_summary

        if (
            content_match
            and summary_match
            and not mismatched_fields
            and snapshot is not None
            and snapshot_semantics_ok
            and content_transition_ok
            and domain_semantics_ok
        ):
            operation.verification_status = AgentVerificationStatus.PASSED.value
            verification_parts = ["预览与落库结果一致"]
            if matched_fields:
                verification_parts.append(f"字段验证通过：{', '.join(matched_fields)}")
            if snapshot_summary:
                verification_parts.append(snapshot_summary)
            if snapshot_semantic_summary:
                verification_parts.append(snapshot_semantic_summary)
            if content_transition_summary:
                verification_parts.append(content_transition_summary)
            if domain_semantic_summary:
                verification_parts.append(domain_semantic_summary)
            operation.verification_summary = "；".join(verification_parts) + "。"
            return

        mismatches: list[str] = []
        if not summary_match:
            mismatches.append("摘要不一致")
        if not content_match:
            mismatches.append("内容 hash 不一致")
        if mismatched_fields:
            mismatches.append(f"字段不一致：{', '.join(mismatched_fields)}")
        if snapshot is None and snapshot_summary:
            mismatches.append(snapshot_summary)
        if snapshot is not None and not snapshot_semantics_ok and snapshot_semantic_summary:
            mismatches.append(snapshot_semantic_summary)
        if snapshot is not None and not content_transition_ok and content_transition_summary:
            mismatches.append(content_transition_summary)
        if not domain_semantics_ok and domain_semantic_summary:
            mismatches.append(domain_semantic_summary)
        operation.verification_status = AgentVerificationStatus.FAILED.value
        operation.verification_summary = "；".join(mismatches)
        raise BadRequestException(f"Operation verification failed: {operation.verification_summary}")

    def _verify_operation_fields(
        self,
        *,
        operation: AgentOperation,
        target: Project | Character | WorldSetting | Volume | Chapter | Scene,
    ) -> tuple[list[str], list[str]]:
        """Verify stable field values for create/update operations."""
        expected_updates = self._field_level_expected_updates(operation)
        if not expected_updates:
            return [], []

        actual_data = _serialize_model(target)
        matched_fields: list[str] = []
        mismatched_fields: list[str] = []
        for field_name, expected_value in expected_updates.items():
            actual_value = actual_data.get(field_name)
            if actual_value == expected_value:
                matched_fields.append(field_name)
            else:
                mismatched_fields.append(field_name)

        execution_result = dict(operation.execution_result or {})
        execution_result["field_verification"] = {
            "matched_fields": list(matched_fields),
            "mismatched_fields": list(mismatched_fields),
        }
        operation.execution_result = execution_result
        return matched_fields, mismatched_fields

    async def _verify_operation_snapshot_linkage(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        operation: AgentOperation,
    ) -> tuple[Snapshot | None, str | None]:
        """Verify that the operation carries a valid snapshot linkage."""
        raw_result = dict(operation.execution_result or {})
        raw_snapshot = raw_result.get("snapshot")
        if not isinstance(raw_snapshot, dict):
            raw_result["snapshot_verification"] = {
                "status": "failed",
                "linkage_status": "failed",
                "semantic_status": "skipped",
                "reason": "missing_snapshot_linkage",
            }
            operation.execution_result = raw_result
            return None, "缺少快照联动"

        snapshot_id = raw_snapshot.get("snapshot_id")
        stage = str(raw_snapshot.get("stage") or "")
        if snapshot_id is None or stage not in {"pre_update", "post_create"}:
            raw_result["snapshot_verification"] = {
                "status": "failed",
                "linkage_status": "failed",
                "semantic_status": "skipped",
                "reason": "invalid_snapshot_linkage",
            }
            operation.execution_result = raw_result
            return None, "快照联动无效"

        try:
            snapshot = await snapshot_service.get(db, id=uuid.UUID(str(snapshot_id)))
        except (NotFoundException, ValueError):
            raw_result["snapshot_verification"] = {
                "status": "failed",
                "linkage_status": "failed",
                "semantic_status": "skipped",
                "reason": "snapshot_missing",
            }
            operation.execution_result = raw_result
            return None, "快照缺失"

        if (
            snapshot.project_id != project_id
            or operation.target_id is None
            or snapshot.target_id != operation.target_id
            or snapshot.target_type != str(operation.target_type)
        ):
            raw_result["snapshot_verification"] = {
                "status": "failed",
                "linkage_status": "failed",
                "semantic_status": "skipped",
                "reason": "snapshot_target_mismatch",
            }
            operation.execution_result = raw_result
            return None, "快照目标不一致"

        raw_result["snapshot_verification"] = {
            "status": "passed",
            "linkage_status": "passed",
            "semantic_status": "pending",
            "snapshot_id": str(snapshot.id),
            "stage": stage,
        }
        operation.execution_result = raw_result
        return snapshot, f"快照联动已校验：{stage}"

    def _verify_operation_snapshot_semantics(
        self,
        *,
        operation: AgentOperation,
        snapshot: Snapshot,
        target: Project | Character | WorldSetting | Volume | Chapter | Scene,
    ) -> tuple[bool, str]:
        """Verify that the post-operation state matches the semantic transition from the snapshot."""
        actual_data = _serialize_model(target)
        expected_data = self._expected_target_from_snapshot(operation=operation, snapshot=snapshot)
        comparable_fields = self._snapshot_semantic_fields(operation=operation, target=target)

        matched_fields: list[str] = []
        mismatched_fields: list[str] = []
        for field_name in comparable_fields:
            if actual_data.get(field_name) == expected_data.get(field_name):
                matched_fields.append(field_name)
            else:
                mismatched_fields.append(field_name)

        execution_result = dict(operation.execution_result or {})
        snapshot_verification = dict(cast(dict[str, Any], execution_result.get("snapshot_verification", {})))
        snapshot_verification["matched_fields"] = matched_fields
        snapshot_verification["mismatched_fields"] = mismatched_fields
        if mismatched_fields:
            snapshot_verification["status"] = "failed"
            snapshot_verification["semantic_status"] = "failed"
            snapshot_verification["reason"] = "snapshot_semantic_mismatch"
            execution_result["snapshot_verification"] = snapshot_verification
            operation.execution_result = execution_result
            return False, f"快照语义不一致：{', '.join(mismatched_fields)}"

        snapshot_verification["status"] = "passed"
        snapshot_verification["semantic_status"] = "passed"
        execution_result["snapshot_verification"] = snapshot_verification
        operation.execution_result = execution_result
        stage = str(snapshot_verification.get("stage") or "unknown")
        return True, f"快照语义已校验：{stage}"

    def _verify_operation_content_transition(
        self,
        *,
        operation: AgentOperation,
        snapshot: Snapshot,
        target: Project | Character | WorldSetting | Volume | Chapter | Scene,
    ) -> tuple[bool, str | None]:
        """Verify content transition semantics for explicit write operations."""
        if operation.tool_name not in {"write_chapter_content", "write_scene_content"}:
            return True, None

        payload = dict(operation.payload or {})
        mode = str(payload.get("mode", "replace"))
        incoming_content = str(payload.get("content", "")).strip()
        previous_content = cast(str | None, snapshot.data.get("content") if isinstance(snapshot.data, dict) else None)
        actual_content = self._target_content(target)
        expected_content = self._apply_text_mode(previous_content, incoming_content, mode)

        checks: dict[str, bool] = {
            "matches_expected_content": actual_content == expected_content,
            "incoming_content_applied": actual_content == incoming_content if mode == "replace" else bool(actual_content and actual_content.endswith(incoming_content)),
        }
        mismatch_reasons: list[str] = []

        if not checks["matches_expected_content"]:
            mismatch_reasons.append("expected_content_mismatch")
        if not checks["incoming_content_applied"]:
            mismatch_reasons.append("incoming_content_not_applied")

        if mode == "append":
            previous_excerpt = (previous_content or "").strip()
            checks["existing_content_retained"] = not previous_excerpt or bool(actual_content and previous_excerpt in actual_content)
            if not checks["existing_content_retained"]:
                mismatch_reasons.append("existing_content_not_retained")

        execution_result = dict(operation.execution_result or {})
        execution_result["content_transition_verification"] = {
            "status": "failed" if mismatch_reasons else "passed",
            "mode": mode,
            "before_content_hash": _hash_text(previous_content),
            "expected_content_hash": _hash_text(expected_content),
            "actual_content_hash": _hash_text(actual_content),
            "checks": checks,
            "mismatch_reasons": mismatch_reasons,
        }
        operation.execution_result = execution_result

        if mismatch_reasons:
            reason_labels = {
                "expected_content_mismatch": "目标正文与预期不一致",
                "incoming_content_not_applied": "新增正文未落库",
                "existing_content_not_retained": "原正文未保留",
            }
            rendered = ", ".join(reason_labels[reason] for reason in mismatch_reasons)
            return False, f"内容迁移不一致：{rendered}"
        return True, f"内容迁移已校验：{mode}"

    async def _verify_operation_domain_semantics(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        operation: AgentOperation,
        target: Project | Character | WorldSetting | Volume | Chapter | Scene,
    ) -> tuple[bool, str | None]:
        """Verify domain-level invariants that are not fully covered by field or content checks."""
        passed_checks: list[str] = []
        failed_checks: list[str] = []

        if operation.tool_name == "update_project_outline" and isinstance(target, Project):
            if (target.story_outline or "").strip():
                passed_checks.append("story_outline_not_empty")
            else:
                failed_checks.append("story_outline_empty")

        if operation.tool_name in {"create_character", "update_character"} and isinstance(target, Character):
            trimmed_name = (target.name or "").strip()
            if not trimmed_name:
                failed_checks.append("character_name_empty")
            else:
                passed_checks.append("character_name_not_empty")

            duplicate_character_stmt = (
                select(Character.id)
                .where(
                    Character.project_id == project_id,
                    func.lower(func.trim(Character.name)) == trimmed_name.lower(),
                    Character.id != target.id,
                )
                .limit(1)
            )
            duplicate_character = (await db.execute(duplicate_character_stmt)).scalar_one_or_none()
            if duplicate_character is not None:
                failed_checks.append("character_name_duplicate")
            else:
                passed_checks.append("character_name_unique")

            profile = target.profile or {}
            if isinstance(profile, dict):
                age = profile.get("age")
                if age is not None:
                    if not isinstance(age, int) or age < 0:
                        failed_checks.append("character_age_invalid")
                    else:
                        passed_checks.append("character_age_valid")

        if operation.tool_name in {"create_world_setting", "update_world_setting"} and isinstance(target, WorldSetting):
            trimmed_name = (target.name or "").strip()
            if not trimmed_name:
                failed_checks.append("world_setting_name_empty")
            else:
                passed_checks.append("world_setting_name_not_empty")

            trimmed_content = (target.content or "").strip()
            if not trimmed_content:
                failed_checks.append("world_setting_content_empty")
            else:
                passed_checks.append("world_setting_content_not_empty")

            normalized_name = trimmed_name.lower()
            duplicate_setting_stmt = (
                select(WorldSetting.id)
                .where(
                    WorldSetting.project_id == project_id,
                    func.lower(func.trim(WorldSetting.name)) == normalized_name,
                    WorldSetting.category == target.category,
                    WorldSetting.id != target.id,
                )
                .limit(1)
            )
            duplicate_setting = (await db.execute(duplicate_setting_stmt)).scalar_one_or_none()
            if duplicate_setting is not None:
                failed_checks.append("world_setting_name_duplicate")
            else:
                passed_checks.append("world_setting_name_unique")

        if operation.tool_name in {"create_volume", "update_volume"} and isinstance(target, Volume):
            if target.project_id != project_id:
                failed_checks.append("volume_project_mismatch")
            else:
                passed_checks.append("volume_project_scope")

            duplicate_volume_stmt = (
                select(Volume.id)
                .where(
                    Volume.project_id == project_id,
                    Volume.volume_number == target.volume_number,
                    Volume.id != target.id,
                )
                .limit(1)
            )
            duplicate_volume = (await db.execute(duplicate_volume_stmt)).scalar_one_or_none()
            if duplicate_volume is not None:
                failed_checks.append("volume_number_duplicate")
            else:
                passed_checks.append("volume_number_unique")

        if operation.tool_name in {"create_chapter", "update_chapter"} and isinstance(target, Chapter):
            if target.volume_id is not None:
                try:
                    volume = await volume_service.get(db, id=target.volume_id)
                except NotFoundException:
                    failed_checks.append("volume_missing")
                else:
                    if volume.project_id != project_id:
                        failed_checks.append("volume_project_mismatch")
                    else:
                        passed_checks.append("volume_scope")

            duplicate_chapter_stmt = (
                select(Chapter.id)
                .where(
                    Chapter.project_id == project_id,
                    Chapter.chapter_number == target.chapter_number,
                    Chapter.id != target.id,
                )
                .limit(1)
            )
            if target.volume_id is None:
                duplicate_chapter_stmt = duplicate_chapter_stmt.where(Chapter.volume_id.is_(None))
            else:
                duplicate_chapter_stmt = duplicate_chapter_stmt.where(Chapter.volume_id == target.volume_id)
            duplicate_chapter = (await db.execute(duplicate_chapter_stmt)).scalar_one_or_none()
            if duplicate_chapter is not None:
                failed_checks.append("chapter_number_duplicate")
            else:
                passed_checks.append("chapter_number_unique")

        if operation.tool_name in {"create_scene", "update_scene"} and isinstance(target, Scene):
            try:
                chapter = await chapter_service.get(db, id=target.chapter_id)
            except NotFoundException:
                failed_checks.append("scene_parent_missing")
            else:
                if chapter.project_id != project_id:
                    failed_checks.append("scene_project_mismatch")
                else:
                    passed_checks.append("scene_project_scope")

            duplicate_scene_stmt = (
                select(Scene.id)
                .where(
                    Scene.chapter_id == target.chapter_id,
                    Scene.scene_order == target.scene_order,
                    Scene.id != target.id,
                )
                .limit(1)
            )
            duplicate_scene = (await db.execute(duplicate_scene_stmt)).scalar_one_or_none()
            if duplicate_scene is not None:
                failed_checks.append("scene_order_duplicate")
            else:
                passed_checks.append("scene_order_unique")

            if target.pov_character_id is not None:
                try:
                    pov_character = await character_service.get(db, id=target.pov_character_id)
                except NotFoundException:
                    failed_checks.append("pov_character_missing")
                else:
                    if pov_character.project_id != project_id:
                        failed_checks.append("pov_character_project_mismatch")
                    else:
                        passed_checks.append("pov_character_scope")

        if not passed_checks and not failed_checks:
            return True, None

        execution_result = dict(operation.execution_result or {})
        execution_result["domain_verification"] = {
            "status": "failed" if failed_checks else "passed",
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
        }
        operation.execution_result = execution_result

        if failed_checks:
            reason_labels = {
                "character_name_empty": "人物名称不能为空",
                "character_name_duplicate": "人物名称重复",
                "character_age_invalid": "人物年龄必须为非负整数",
                "world_setting_name_empty": "设定名称不能为空",
                "world_setting_content_empty": "设定内容不能为空",
                "world_setting_name_duplicate": "同分类下设定名称重复",
                "story_outline_empty": "项目大纲不能为空",
                "volume_number_duplicate": "卷序号重复",
                "volume_missing": "卷不存在",
                "volume_project_mismatch": "章节卷归属错误",
                "volume_project_scope": "卷不属于当前项目",
                "chapter_number_duplicate": "章节序号重复",
                "scene_parent_missing": "场景父章节缺失",
                "scene_project_mismatch": "场景不属于当前项目",
                "scene_order_duplicate": "场景序号重复",
                "pov_character_missing": "POV 人物不存在",
                "pov_character_project_mismatch": "POV 人物不属于当前项目",
            }
            rendered = ", ".join(reason_labels.get(reason, reason) for reason in failed_checks)
            return False, f"领域语义不一致：{rendered}"

        return True, f"领域语义已校验：{', '.join(passed_checks)}"

    def _expected_target_from_snapshot(
        self,
        *,
        operation: AgentOperation,
        snapshot: Snapshot,
    ) -> dict[str, Any]:
        """Build the expected post-operation state using the snapshot and operation payload."""
        expected_data = dict(snapshot.data or {})
        payload = dict(operation.payload or {})

        if operation.tool_name in {
            "update_project_outline",
            "update_character",
            "update_world_setting",
            "update_volume",
            "update_chapter",
            "update_scene",
        }:
            updates = payload.get("updates", {})
            if isinstance(updates, dict):
                expected_data.update(_json_ready(updates))
            return expected_data

        if operation.tool_name in {"write_chapter_content", "write_scene_content"}:
            existing_content = cast(str | None, expected_data.get("content"))
            next_content = self._apply_text_mode(
                existing_content,
                str(payload.get("content", "")),
                str(payload.get("mode", "replace")),
            )
            expected_data["content"] = next_content
            return expected_data

        return expected_data

    def _snapshot_semantic_fields(
        self,
        *,
        operation: AgentOperation,
        target: Project | Character | WorldSetting | Volume | Chapter | Scene,
    ) -> list[str]:
        """Return stable business fields used for snapshot semantic verification."""
        if isinstance(target, Project):
            return [
                "name",
                "genre",
                "target_audience",
                "target_word_count",
                "status",
                "summary",
                "story_outline",
                "notes",
                "meta",
            ]
        if isinstance(target, Character):
            return ["project_id", "name", "role", "profile", "relationships", "arc_state", "notes"]
        if isinstance(target, WorldSetting):
            return ["project_id", "category", "name", "content", "meta"]
        if isinstance(target, Volume):
            return ["project_id", "volume_number", "title", "outline", "notes"]
        if isinstance(target, Chapter):
            return ["project_id", "volume_id", "chapter_number", "title", "outline", "content", "status", "notes"]
        if isinstance(target, Scene):
            return ["chapter_id", "scene_order", "pov_character_id", "location", "content", "meta"]
        raise BadRequestException(f"Unsupported target for snapshot semantic verification: {operation.tool_name}")

    async def _create_operation_snapshot(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        operation: AgentOperation,
        target_type: str,
        target_id: uuid.UUID,
        data: dict[str, Any],
        stage: Literal["pre_update", "post_create"],
    ) -> Snapshot:
        """Create and record the snapshot linked to one operation execution."""
        snapshot = await snapshot_service.create_snapshot(
            db,
            project_id=project_id,
            target_type=target_type,
            target_id=target_id,
            data=data,
        )
        execution_result = dict(operation.execution_result or {})
        execution_result["snapshot"] = {
            "snapshot_id": str(snapshot.id),
            "target_type": snapshot.target_type,
            "target_id": str(snapshot.target_id),
            "stage": stage,
        }
        operation.execution_result = execution_result
        return snapshot

    def _field_level_expected_updates(self, operation: AgentOperation) -> dict[str, Any]:
        """Return comparable expected field values for create/update operations."""
        if operation.tool_name in {
            "create_volume",
            "create_character",
            "create_world_setting",
            "create_chapter",
            "create_scene",
        }:
            comparable_fields: dict[str, Any] = {}
            for field_name, value in operation.payload.items():
                comparable_fields[str(field_name)] = _json_ready(value)
            return comparable_fields

        if operation.tool_name not in {
            "update_project_outline",
            "update_character",
            "update_world_setting",
            "update_volume",
            "update_chapter",
            "update_scene",
        }:
            return {}

        raw_updates = operation.payload.get("updates", {})
        if not isinstance(raw_updates, dict):
            return {}

        expected_updates: dict[str, Any] = {}
        for field_name, value in raw_updates.items():
            if field_name == "content" and operation.tool_name in {"update_chapter", "update_scene"}:
                continue
            expected_updates[str(field_name)] = _json_ready(value)
        return expected_updates

    async def _load_operation_target(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        operation: AgentOperation,
    ) -> Project | Character | WorldSetting | Volume | Chapter | Scene:
        if operation.target_id is None:
            raise BadRequestException("Executed operation is missing target_id")
        payload = operation.payload
        request_context: dict[str, Any] = {}
        if operation.tool_name == "update_project_outline":
            return await self._resolve_project(
                db,
                project_id=project_id,
                payload={**payload, "project_id": str(operation.target_id)},
                request_context=request_context,
            )
        if operation.tool_name in {"create_character", "update_character"}:
            return await self._resolve_character(
                db,
                project_id=project_id,
                payload={**payload, "character_id": str(operation.target_id)},
                request_context=request_context,
            )
        if operation.tool_name in {"create_world_setting", "update_world_setting"}:
            return await self._resolve_world_setting(
                db,
                project_id=project_id,
                payload={**payload, "setting_id": str(operation.target_id)},
                request_context=request_context,
            )
        if operation.tool_name in {"create_volume", "update_volume"}:
            return await self._resolve_volume(
                db,
                project_id=project_id,
                payload={**payload, "volume_id": str(operation.target_id)},
                request_context=request_context,
            )
        if operation.tool_name in {"create_chapter", "update_chapter", "write_chapter_content"}:
            return await self._resolve_chapter(
                db,
                project_id=project_id,
                payload={**payload, "chapter_id": str(operation.target_id)},
                request_context=request_context,
            )
        if operation.tool_name in {"create_scene", "update_scene", "write_scene_content"}:
            return await self._resolve_scene(
                db,
                project_id=project_id,
                payload={**payload, "scene_id": str(operation.target_id)},
                request_context=request_context,
            )
        raise BadRequestException(f"Unsupported tool '{operation.tool_name}' for verification")

    def _target_summary(self, target: Project | Character | WorldSetting | Volume | Chapter | Scene, tool_name: str) -> str:
        if tool_name == "write_chapter_content" and isinstance(target, Chapter):
            return _excerpt(target.content) or ""
        if tool_name == "write_scene_content" and isinstance(target, Scene):
            return _excerpt(target.content) or ""
        if isinstance(target, Project):
            return self._project_summary(target)
        if isinstance(target, Character):
            return self._character_summary(target)
        if isinstance(target, WorldSetting):
            return self._world_setting_summary(target)
        if isinstance(target, Volume):
            return self._volume_summary(target)
        if isinstance(target, Chapter):
            return self._chapter_summary(target)
        if isinstance(target, Scene):
            return self._scene_summary(target)
        raise BadRequestException(f"Unsupported target for tool '{tool_name}'")

    def _target_content(self, target: Project | Character | WorldSetting | Volume | Chapter | Scene) -> str | None:
        if isinstance(target, Project):
            return target.story_outline
        if isinstance(target, Character):
            return target.notes
        if isinstance(target, WorldSetting):
            return target.content
        if isinstance(target, Volume):
            return target.outline
        if isinstance(target, Chapter):
            return target.content
        if isinstance(target, Scene):
            return target.content
        return None

    def _aggregate_run_verification(
        self,
        operations: list[AgentOperation],
        *,
        continuity_subtask: AgentSubtask | None,
    ) -> tuple[str, str]:
        if continuity_subtask is not None and continuity_subtask.status == AgentSubtaskStatus.FAILED.value:
            return AgentVerificationStatus.FAILED.value, continuity_subtask.error_message or "Continuity gate failed."
        failed = [operation for operation in operations if operation.verification_status == AgentVerificationStatus.FAILED.value]
        if failed:
            labels = ", ".join(operation.description for operation in failed[:3])
            return AgentVerificationStatus.FAILED.value, f"以下步骤未通过验证：{labels}"
        if not operations:
            return AgentVerificationStatus.SKIPPED.value, "No stateful operations to verify."
        return AgentVerificationStatus.PASSED.value, "All operations were verified against persisted results."

    def _upsert_run_hook_trace(
        self,
        run: AgentRun,
        entry: HookTraceEntry,
    ) -> None:
        """Insert or replace one hook lifecycle entry inside run metadata."""
        next_meta = dict(run.meta or {})
        raw_trace = cast(list[dict[str, Any]], next_meta.get("hook_trace", []))
        trace: list[dict[str, Any]] = [dict(item) for item in raw_trace]
        serialized = entry.model_dump(mode="json")
        for index, existing in enumerate(trace):
            if existing.get("hook_name") == entry.hook_name:
                trace[index] = serialized
                break
        else:
            trace.append(serialized)
        next_meta["hook_trace"] = trace
        run.meta = next_meta

    def _update_capability_execution_record(
        self,
        run: AgentRun,
        *,
        phase_name: str,
        capability_id: str,
        status: str,
        output_summary: str,
    ) -> None:
        """Update one capability execution record inside the serialized run contract."""
        next_meta = dict(run.meta or {})
        raw_contract = cast(dict[str, Any], next_meta.get("permission_matrix", {}))
        raw_phases = cast(list[dict[str, Any]], raw_contract.get("phases", []))
        for phase in raw_phases:
            if str(phase.get("phase")) != phase_name:
                continue
            for capability in cast(list[dict[str, Any]], phase.get("capabilities", [])):
                if str(capability.get("capability_id")) != capability_id:
                    continue
                record = dict(cast(dict[str, Any], capability.get("execution_record", {})))
                if not record:
                    continue
                record["status"] = status
                record["output_summary"] = output_summary
                capability["execution_record"] = record
        raw_contract["phases"] = raw_phases
        next_meta["permission_matrix"] = raw_contract
        run.meta = next_meta

    async def _safe_get_operation(
        self,
        db: AsyncSession,
        *,
        operation_id: uuid.UUID,
    ) -> AgentOperation | None:
        result = await db.execute(select(AgentOperation).where(AgentOperation.id == operation_id))
        return result.scalar_one_or_none()


agent_workflow_service = AgentWorkflowService()
