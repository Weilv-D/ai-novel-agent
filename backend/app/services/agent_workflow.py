"""Planner and executor for the project-scoped agent workflow."""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import re
import uuid
from datetime import UTC, datetime
from textwrap import dedent
from typing import Any, Literal, cast

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import desc, select
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
from app.models.chapter import Chapter, Scene
from app.models.character import Character
from app.models.project import Project
from app.models.world_setting import WorldSetting
from app.schemas.agent import (
    AgentMessageResponse,
    AgentOperationResponse,
    AgentProfileResponse,
    AgentRunActionResponse,
    AgentRunResponse,
    AgentSkillCatalogResponse,
    AgentSkillSummaryResponse,
    AgentSubtaskResponse,
    AgentThreadMessageResponse,
    AgentThreadResponse,
    AgentThreadStateResponse,
    OperationPreview,
)
from app.schemas.chapter import ChapterCreate, ChapterUpdate, SceneCreate, SceneUpdate
from app.schemas.character import CharacterCreate, CharacterUpdate
from app.schemas.world_setting import WorldSettingCreate, WorldSettingUpdate
from app.services.agent_skill import AgentSkillBundle, agent_skill_service
from app.services.chapter import chapter_service, scene_service
from app.services.character import character_service
from app.services.llm import LLMService, llm_service
from app.services.project import project_service
from app.services.snapshot import snapshot_service
from app.services.world_setting import world_setting_service

logger = logging.getLogger(__name__)

TOOL_NAMES = {
    "create_character",
    "update_character",
    "create_world_setting",
    "update_world_setting",
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


class CRUDAgentThread:
    """Persistence helpers for project threads."""

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
            next_meta = dict(existing.meta or {})
            if next_meta.get("project_name") != project.name or next_meta.get("profile_id") != project.agent_profile_id:
                next_meta["project_name"] = project.name
                next_meta["profile_id"] = project.agent_profile_id
                existing.meta = next_meta
                await db.flush()
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
        db.add(thread)
        await db.flush()
        await db.refresh(thread)
        return thread


class CRUDAgentMessage:
    """Persistence helpers for thread messages."""

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

        checkpoint = await self._maybe_compact_thread(
            db,
            thread=thread,
            project=project,
            profile_id=profile_id,
            history=full_history,
            recent_runs=recent_runs,
            request_context=request_context,
        )
        history = await self._planner_history(
            db,
            thread_id=thread.id,
            latest_checkpoint=checkpoint,
        )
        context_data = await self._load_project_context(
            db,
            project=project,
            request_context=request_context,
            latest_checkpoint=checkpoint,
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
        )
        classified_operations = self._classify_operations(planned_operations)
        planned_subtasks = self._build_subtasks(
            planner_output=planner_output,
            operations=classified_operations,
            context_data=context_data,
            latest_checkpoint=checkpoint,
        )

        run = await self.run_store.create(
            db,
            thread_id=thread.id,
            project_id=thread.project_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            revision_of_run_id=prior_run.id if prior_run is not None else None,
            summary=planner_output.summary,
            warning_message=planner_output.warning_message,
            meta={
                "request_context": request_context,
                "raw_operation_count": len(classified_operations),
                "profile_id": profile_id,
                "checkpoint_id": str(checkpoint.id) if checkpoint is not None else None,
                "skill_snapshot": self._build_skill_snapshot(skill_bundle, classified_operations),
            },
        )
        await self.operation_store.create_many(db, run_id=run.id, operations=classified_operations)
        await self.subtask_store.create_many(db, run_id=run.id, subtasks=planned_subtasks)
        await self.run_store.supersede_pending_runs(db, thread_id=thread.id, keep_run_id=run.id)

        return AgentThreadMessageResponse(
            thread=self._thread_response(thread),
            user_message=self._message_response(user_message),
            assistant_message=self._message_response(assistant_message),
            run=await self._run_response(db, run),
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
                failing_operation_id = operation.id
                await self._execute_operation(
                    db,
                    project_id=run.project_id,
                    request_context=request_context,
                    operation=operation,
                )
                await self._verify_operation(
                    db,
                    project_id=run.project_id,
                    operation=operation,
                )
            run.status = AgentRunStatus.COMPLETED.value
            run.completed_at = datetime.now(UTC)
            run.warning_message = self._execution_warning(operations)
            run.verification_status, run.verification_summary = self._aggregate_run_verification(
                operations,
                continuity_subtask=continuity_subtask,
            )
            if run.verification_status != AgentVerificationStatus.PASSED.value:
                raise BadRequestException(run.verification_summary or "Run verification failed")
            await db.flush()
        except Exception as exc:
            logger.exception("Agent run %s failed", run_id_value)
            await db.rollback()
            failed_run = await self.run_store.get(db, run_id_value)
            failed_run.status = AgentRunStatus.FAILED.value
            failed_run.error_message = str(exc)
            failed_run.completed_at = datetime.now(UTC)
            failed_run.verification_status = AgentVerificationStatus.FAILED.value
            failed_run.verification_summary = str(exc)
            if failing_operation_id is not None:
                failed_operation = await self._safe_get_operation(db, operation_id=failing_operation_id)
                if failed_operation is not None:
                    failed_operation.status = AgentOperationStatus.FAILED.value
                    failed_operation.error_message = str(exc)
                    failed_operation.verification_status = AgentVerificationStatus.FAILED.value
                    failed_operation.verification_summary = str(exc)
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

        return AgentRunActionResponse(run=await self._run_response(db, run))

    async def _load_project_context(
        self,
        db: AsyncSession,
        *,
        project: Project,
        request_context: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None = None,
    ) -> dict[str, Any]:
        characters = await character_service.get_by_project(db, project_id=project.id, limit=20)
        world_settings = await world_setting_service.get_by_project(db, project_id=project.id, limit=20)
        chapters = await chapter_service.get_by_project(db, project_id=project.id, limit=40)

        context_data: dict[str, Any] = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "genre": project.genre,
                "summary": project.summary,
            },
            "characters": [
                {
                    "id": str(character.id),
                    "name": character.name,
                    "role": character.role,
                }
                for character in characters
            ],
            "world_settings": [
                {
                    "id": str(setting.id),
                    "name": setting.name,
                    "category": setting.category,
                }
                for setting in world_settings
            ],
            "chapters": [
                {
                    "id": str(chapter.id),
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                }
                for chapter in chapters
            ],
            "request_context": request_context,
            "agent_profile_id": project.agent_profile_id,
        }
        if latest_checkpoint is not None:
            context_data["latest_checkpoint"] = {
                "id": str(latest_checkpoint.id),
                "profile_id": latest_checkpoint.profile_id,
                "thread_summary": latest_checkpoint.thread_summary,
                "active_object_bundle": latest_checkpoint.active_object_bundle,
                "recent_run_digest": latest_checkpoint.recent_run_digest,
            }

        chapter_id = request_context.get("chapter_id")
        if chapter_id:
            try:
                chapter = await chapter_service.get(db, id=uuid.UUID(str(chapter_id)))
                scenes = await scene_service.get_by_chapter(db, chapter_id=chapter.id, limit=20)
                context_data["current_chapter"] = {
                    "id": str(chapter.id),
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "content": _excerpt(chapter.content, length=400),
                }
                context_data["current_scenes"] = [
                    {
                        "id": str(scene.id),
                        "scene_order": scene.scene_order,
                        "location": scene.location,
                    }
                    for scene in scenes
                ]
            except Exception:
                logger.debug("Failed to load chapter context for %s", chapter_id)

        scene_id = request_context.get("scene_id")
        if scene_id:
            try:
                scene = await scene_service.get(db, id=uuid.UUID(str(scene_id)))
                context_data["current_scene"] = {
                    "id": str(scene.id),
                    "scene_order": scene.scene_order,
                    "location": scene.location,
                    "content": _excerpt(scene.content, length=400),
                }
            except Exception:
                logger.debug("Failed to load scene context for %s", scene_id)

        character_id = request_context.get("character_id")
        if character_id:
            try:
                character = await character_service.get(db, id=uuid.UUID(str(character_id)))
                context_data["current_character"] = {
                    "id": str(character.id),
                    "name": character.name,
                    "role": character.role,
                }
            except Exception:
                logger.debug("Failed to load character context for %s", character_id)

        return context_data

    async def _planner_history(
        self,
        db: AsyncSession,
        *,
        thread_id: uuid.UUID,
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> list[AgentMessage]:
        limit = 6 if latest_checkpoint is not None else 12
        return await self.message_store.list_recent_history(db, thread_id=thread_id, limit=limit)

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
    ) -> AgentThreadCheckpoint | None:
        latest_checkpoint = await self.checkpoint_store.latest_by_thread(db, thread_id=thread.id)
        total_chars = sum(len(message.content) for message in history) + sum(len(run.summary or "") for run in recent_runs)
        should_compact = (
            len(history) >= COMPACTION_MESSAGE_THRESHOLD
            or len(recent_runs) >= COMPACTION_RUN_THRESHOLD
            or total_chars >= COMPACTION_CHAR_THRESHOLD
        )
        if not should_compact:
            return latest_checkpoint

        if latest_checkpoint is not None:
            if (
                latest_checkpoint.source_message_count >= len(history)
                and latest_checkpoint.source_run_count >= len(recent_runs)
                and latest_checkpoint.total_context_characters >= total_chars
            ):
                return latest_checkpoint

        compact_context = {
            "project": {"name": project.name, "genre": project.genre, "summary": project.summary},
            "request_context": request_context,
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
                for run in recent_runs[:6]
            ]
        }
        return await self.checkpoint_store.create(
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

    async def _plan_with_llm(
        self,
        *,
        user_message: str,
        context_data: dict[str, Any],
        history: list[AgentMessage],
        prior_run: AgentRun | None,
        skill_bundle: AgentSkillBundle,
    ) -> PlannerOutput:
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

        prompt = dedent(
            f"""
            {skill_bundle.planner.prompt_block()}

            当前项目上下文：
            {json.dumps(context_data, ensure_ascii=False)}

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

    async def _prepare_operations(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        request_context: dict[str, Any],
        operations: list[PlannedOperationSpec],
    ) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []
        for operation in operations:
            normalized = await self._normalize_operation_payload(
                db,
                project_id=project_id,
                request_context=request_context,
                operation=operation,
            )
            prepared.append(normalized)
        return prepared

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

        if tool_name == "create_character":
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
                after_summary=f"{normalized_payload['name']} / {normalized_payload['category']}",
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
            normalized_payload = {
                "chapter_id": str(chapter.id),
                "mode": payload.get("mode", "replace"),
                "content": str(payload.get("content", "")).strip(),
            }
            if not normalized_payload["content"]:
                raise BadRequestException("write_chapter_content requires content")
            next_content = self._apply_text_mode(chapter.content, normalized_payload["content"], normalized_payload["mode"])
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
            normalized_payload = {
                "scene_id": str(scene.id),
                "mode": payload.get("mode", "replace"),
                "content": str(payload.get("content", "")).strip(),
            }
            if not normalized_payload["content"]:
                raise BadRequestException("write_scene_content requires content")
            next_content = self._apply_text_mode(scene.content, normalized_payload["content"], normalized_payload["mode"])
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

        if tool_name == "create_character":
            character_in = CharacterCreate(project_id=project_id, **payload)
            character = await character_service.create_with_project(db, obj_in=character_in, project_id=project_id)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="character",
                target_id=character.id,
                data=_serialize_model(character),
            )
            operation.target_id = character.id
            operation.target_display = character.name
            operation.execution_result = {"created_id": str(character.id)}

        elif tool_name == "update_character":
            character = await self._resolve_character(db, project_id=project_id, payload=payload, request_context=request_context)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="character",
                target_id=character.id,
                data=_serialize_model(character),
            )
            updated_character = await character_service.update(
                db,
                db_obj=character,
                obj_in=CharacterUpdate(**cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_character.id
            operation.target_display = updated_character.name
            operation.execution_result = {"updated_id": str(updated_character.id)}

        elif tool_name == "create_world_setting":
            world_setting_in = WorldSettingCreate(project_id=project_id, **payload)
            setting = await world_setting_service.create_with_project(db, obj_in=world_setting_in, project_id=project_id)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="world_setting",
                target_id=setting.id,
                data=_serialize_model(setting),
            )
            operation.target_id = setting.id
            operation.target_display = setting.name
            operation.execution_result = {"created_id": str(setting.id)}

        elif tool_name == "update_world_setting":
            setting = await self._resolve_world_setting(db, project_id=project_id, payload=payload, request_context=request_context)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="world_setting",
                target_id=setting.id,
                data=_serialize_model(setting),
            )
            updated_setting = await world_setting_service.update(
                db,
                db_obj=setting,
                obj_in=WorldSettingUpdate(**cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_setting.id
            operation.target_display = updated_setting.name
            operation.execution_result = {"updated_id": str(updated_setting.id)}

        elif tool_name == "create_chapter":
            chapter_in = ChapterCreate(project_id=project_id, **payload)
            chapter = await chapter_service.create_with_project(db, obj_in=chapter_in, project_id=project_id)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="chapter",
                target_id=chapter.id,
                data=_serialize_model(chapter),
            )
            operation.target_id = chapter.id
            operation.target_display = f"第{chapter.chapter_number}章 {chapter.title or ''}".strip()
            operation.execution_result = {"created_id": str(chapter.id)}

        elif tool_name == "update_chapter":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="chapter",
                target_id=chapter.id,
                data=_serialize_model(chapter),
            )
            updated_chapter = await chapter_service.update(
                db,
                db_obj=chapter,
                obj_in=ChapterUpdate(**cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_chapter.id
            operation.target_display = f"第{updated_chapter.chapter_number}章 {updated_chapter.title or ''}".strip()
            operation.execution_result = {"updated_id": str(updated_chapter.id)}

        elif tool_name == "write_chapter_content":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="chapter",
                target_id=chapter.id,
                data=_serialize_model(chapter),
            )
            next_content = self._apply_text_mode(chapter.content, str(payload["content"]), str(payload.get("mode", "replace")))
            updated_chapter = await chapter_service.update(
                db,
                db_obj=chapter,
                obj_in=ChapterUpdate(content=next_content),
            )
            operation.target_id = updated_chapter.id
            operation.target_display = f"第{updated_chapter.chapter_number}章 {updated_chapter.title or ''}".strip()
            operation.execution_result = {"updated_id": str(updated_chapter.id)}

        elif tool_name == "create_scene":
            chapter = await self._resolve_chapter(db, project_id=project_id, payload=payload, request_context=request_context)
            scene_in = SceneCreate(**payload, chapter_id=chapter.id)
            scene = await scene_service.create_with_chapter(db, obj_in=scene_in, chapter_id=chapter.id)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="scene",
                target_id=scene.id,
                data=_serialize_model(scene),
            )
            operation.target_id = scene.id
            operation.target_display = f"场景 {scene.scene_order}"
            operation.execution_result = {"created_id": str(scene.id)}

        elif tool_name == "update_scene":
            scene = await self._resolve_scene(db, project_id=project_id, payload=payload, request_context=request_context)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="scene",
                target_id=scene.id,
                data=_serialize_model(scene),
            )
            updated_scene = await scene_service.update(
                db,
                db_obj=scene,
                obj_in=SceneUpdate(**cast(dict[str, Any], payload["updates"])),
            )
            operation.target_id = updated_scene.id
            operation.target_display = f"场景 {updated_scene.scene_order}"
            operation.execution_result = {"updated_id": str(updated_scene.id)}

        elif tool_name == "write_scene_content":
            scene = await self._resolve_scene(db, project_id=project_id, payload=payload, request_context=request_context)
            await snapshot_service.create_snapshot(
                db,
                project_id=project_id,
                target_type="scene",
                target_id=scene.id,
                data=_serialize_model(scene),
            )
            next_content = self._apply_text_mode(scene.content, str(payload["content"]), str(payload.get("mode", "replace")))
            updated_scene = await scene_service.update(
                db,
                db_obj=scene,
                obj_in=SceneUpdate(content=next_content),
            )
            operation.target_id = updated_scene.id
            operation.target_display = f"场景 {updated_scene.scene_order}"
            operation.execution_result = {"updated_id": str(updated_scene.id)}

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

    def _filter_world_setting_create_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        category = str(payload.get("category") or "other")
        normalized = {
            "name": str(payload.get("name", "")).strip(),
            "category": category,
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
                updates[key] = payload[key]
        self._validate_schema(WorldSettingUpdate, **updates)
        return updates

    async def _filter_chapter_create_payload(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        chapter_number = payload.get("chapter_number")
        if chapter_number is None:
            chapters = await chapter_service.get_by_project(db, project_id=project_id, limit=200)
            chapter_number = max((chapter.chapter_number for chapter in chapters), default=0) + 1
        normalized = {
            "chapter_number": int(chapter_number),
            "title": payload.get("title"),
            "outline": payload.get("outline"),
            "content": payload.get("content"),
            "status": payload.get("status", "draft"),
            "notes": payload.get("notes"),
            "volume_id": payload.get("volume_id"),
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
            "scene_order": int(scene_order),
            "pov_character_id": pov_character_id,
            "location": payload.get("location"),
            "content": payload.get("content"),
            "meta": cast(dict[str, Any], payload.get("meta", {})),
        }
        self._validate_schema(SceneCreate, chapter_id=chapter.id, **normalized)
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
            return "本次执行已完成持久化；记忆与依赖未自动刷新，如有需要请手动复核。"
        return None

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

    async def _run_response(self, db: AsyncSession, run: AgentRun) -> AgentRunResponse:
        operations = await self.operation_store.list_by_run(db, run_id=run.id)
        subtasks = await self.subtask_store.list_by_run(db, run_id=run.id)
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
            meta=run.meta or {},
            confirmed_at=run.confirmed_at,
            secondary_confirmed_at=run.secondary_confirmed_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
            operations=[self._operation_response(operation) for operation in operations],
            subtasks=[self._subtask_response(subtask) for subtask in subtasks],
        )

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
        return AgentSubtaskResponse(
            id=subtask.id,
            run_id=subtask.run_id,
            position=subtask.position,
            role=cast(Any, subtask.role),
            title=subtask.title,
            status=cast(Any, subtask.status),
            summary=subtask.summary,
            error_message=subtask.error_message,
            meta=subtask.meta or {},
            created_at=subtask.created_at,
            updated_at=subtask.updated_at,
        )

    def _classify_operations(self, operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Attach permission and risk metadata to planner operations."""
        classified: list[dict[str, Any]] = []
        content_rewrite_indexes: list[int] = []

        for index, operation in enumerate(operations):
            enriched = dict(operation)
            tool_name = str(enriched["tool_name"])
            payload = cast(dict[str, Any], enriched.get("payload", {}))
            permission_level = AgentPermissionLevel.STANDARD_WRITE.value
            risk_level = AgentRiskLevel.MEDIUM.value
            requires_secondary_confirmation = False

            content_candidate = self._operation_content_candidate(enriched)
            touches_content = content_candidate is not None

            if tool_name in {"write_chapter_content", "write_scene_content"}:
                mode = str(payload.get("mode", "replace"))
                if mode == "append":
                    risk_level = AgentRiskLevel.MEDIUM.value
                else:
                    risk_level = AgentRiskLevel.HIGH.value if len(content_candidate or "") >= 280 else AgentRiskLevel.MEDIUM.value
                if mode == "replace" and len(content_candidate or "") >= 280:
                    permission_level = AgentPermissionLevel.HIGH_RISK_WRITE.value
                    requires_secondary_confirmation = True
                    content_rewrite_indexes.append(index)
            elif tool_name in {"update_chapter", "update_scene"} and touches_content:
                if len(content_candidate or "") >= 280:
                    permission_level = AgentPermissionLevel.HIGH_RISK_WRITE.value
                    risk_level = AgentRiskLevel.HIGH.value
                    requires_secondary_confirmation = True
                    content_rewrite_indexes.append(index)
                else:
                    risk_level = AgentRiskLevel.MEDIUM.value
            elif tool_name in {"create_chapter", "create_scene"} and touches_content:
                risk_level = AgentRiskLevel.MEDIUM.value
            elif tool_name in {"update_character", "update_world_setting"}:
                risk_level = AgentRiskLevel.MEDIUM.value
            else:
                risk_level = AgentRiskLevel.LOW.value

            enriched["permission_level"] = permission_level
            enriched["risk_level"] = risk_level
            enriched["requires_secondary_confirmation"] = requires_secondary_confirmation
            enriched["verification_status"] = AgentVerificationStatus.PENDING.value
            classified.append(enriched)

        if len(content_rewrite_indexes) > 1:
            for index in content_rewrite_indexes:
                classified[index]["permission_level"] = AgentPermissionLevel.HIGH_RISK_WRITE.value
                classified[index]["risk_level"] = AgentRiskLevel.HIGH.value
                classified[index]["requires_secondary_confirmation"] = True

        return classified

    def _build_subtasks(
        self,
        *,
        planner_output: PlannerOutput,
        operations: list[dict[str, Any]],
        context_data: dict[str, Any],
        latest_checkpoint: AgentThreadCheckpoint | None,
    ) -> list[dict[str, Any]]:
        """Build internal subtasks that mirror planner/researcher/writer/editor/continuity roles."""
        provided_by_role = {
            subtask.role: subtask
            for subtask in planner_output.subtasks
        }

        current_objects = [
            f"{key}:{value['id']}"
            for key, value in context_data.items()
            if key.startswith("current_") and isinstance(value, dict) and value.get("id")
        ]
        researcher_summary = (
            f"已装配项目上下文，人物 {len(cast(list[Any], context_data.get('characters', [])))} / "
            f"设定 {len(cast(list[Any], context_data.get('world_settings', [])))} / "
            f"章节 {len(cast(list[Any], context_data.get('chapters', [])))}。"
        )
        if current_objects:
            researcher_summary += f" 当前聚焦：{', '.join(current_objects)}。"
        if latest_checkpoint is not None:
            researcher_summary += f" 已参考 checkpoint {latest_checkpoint.id}。"

        writer_tools = {
            "write_chapter_content",
            "write_scene_content",
            "create_chapter",
            "create_scene",
        }
        writer_ops = [operation for operation in operations if operation["tool_name"] in writer_tools and self._operation_content_candidate(operation)]
        editor_ops = [
            operation
            for operation in operations
            if operation["tool_name"] in {"update_character", "update_world_setting", "update_chapter", "update_scene"}
        ]

        synthesized: list[PlannedSubtaskSpec] = [
            PlannedSubtaskSpec(
                role="planner",
                title="Planner blueprint",
                status="completed",
                summary=_excerpt(planner_output.summary or planner_output.assistant_message, length=SUBTASK_SUMMARY_LIMIT),
            ),
            PlannedSubtaskSpec(
                role="researcher",
                title="Context bundle",
                status="completed",
                summary=_excerpt(researcher_summary, length=SUBTASK_SUMMARY_LIMIT),
            ),
            PlannedSubtaskSpec(
                role="writer",
                title="Writer candidate",
                status="completed" if writer_ops else "skipped",
                summary=_excerpt(
                    f"生成 {len(writer_ops)} 个正文候选，全部在 planning 阶段完成。"
                    if writer_ops
                    else "本轮无需生成正文候选。",
                    length=SUBTASK_SUMMARY_LIMIT,
                ),
            ),
            PlannedSubtaskSpec(
                role="editor",
                title="Editor diff",
                status="completed" if editor_ops else "skipped",
                summary=_excerpt(
                    f"整理 {len(editor_ops)} 个结构化修改步骤。"
                    if editor_ops
                    else "本轮无需结构化 patch/diff。",
                    length=SUBTASK_SUMMARY_LIMIT,
                ),
            ),
            PlannedSubtaskSpec(
                role="continuity",
                title="Continuity gate",
                status="planned",
                summary="执行前将验证目标对象、写入一致性与多步修改冲突。",
            ),
        ]

        merged: list[dict[str, Any]] = []
        for synthesized_subtask in synthesized:
            chosen = provided_by_role.get(synthesized_subtask.role, synthesized_subtask)
            merged.append(
                {
                    "role": chosen.role,
                    "title": chosen.title,
                    "status": chosen.status,
                    "summary": _excerpt(chosen.summary, length=SUBTASK_SUMMARY_LIMIT),
                    "error_message": chosen.error_message,
                    "meta": chosen.meta,
                }
            )
        return merged

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

        content_match = (
            operation.preview_content_hash is None
            or operation.preview_content_hash == operation.persisted_content_hash
        )
        summary_match = preview.after_summary is None or preview.after_summary == actual_summary

        if content_match and summary_match:
            operation.verification_status = AgentVerificationStatus.PASSED.value
            operation.verification_summary = "预览与落库结果一致。"
            return

        mismatches: list[str] = []
        if not summary_match:
            mismatches.append("摘要不一致")
        if not content_match:
            mismatches.append("内容 hash 不一致")
        operation.verification_status = AgentVerificationStatus.FAILED.value
        operation.verification_summary = "；".join(mismatches)
        raise BadRequestException(f"Operation verification failed: {operation.verification_summary}")

    async def _load_operation_target(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        operation: AgentOperation,
    ) -> Character | WorldSetting | Chapter | Scene:
        if operation.target_id is None:
            raise BadRequestException("Executed operation is missing target_id")
        payload = operation.payload
        request_context: dict[str, Any] = {}
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

    def _target_summary(self, target: Character | WorldSetting | Chapter | Scene, tool_name: str) -> str:
        if tool_name == "write_chapter_content" and isinstance(target, Chapter):
            return _excerpt(target.content) or ""
        if tool_name == "write_scene_content" and isinstance(target, Scene):
            return _excerpt(target.content) or ""
        if isinstance(target, Character):
            return self._character_summary(target)
        if isinstance(target, WorldSetting):
            return self._world_setting_summary(target)
        if isinstance(target, Chapter):
            return self._chapter_summary(target)
        if isinstance(target, Scene):
            return self._scene_summary(target)
        raise BadRequestException(f"Unsupported target for tool '{tool_name}'")

    def _target_content(self, target: Character | WorldSetting | Chapter | Scene) -> str | None:
        if isinstance(target, Character):
            return target.notes
        if isinstance(target, WorldSetting):
            return target.content
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

    async def _safe_get_operation(
        self,
        db: AsyncSession,
        *,
        operation_id: uuid.UUID,
    ) -> AgentOperation | None:
        result = await db.execute(select(AgentOperation).where(AgentOperation.id == operation_id))
        return result.scalar_one_or_none()


agent_workflow_service = AgentWorkflowService()
