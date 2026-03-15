"""Persistent models for the agent workflow runtime."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AgentMessageRole(str, Enum):
    """Message roles stored in a thread."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AgentRunStatus(str, Enum):
    """Lifecycle states for an agent run."""

    DRAFT = "draft"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_HIGH_RISK_CONFIRMATION = "awaiting_high_risk_confirmation"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class AgentOperationStatus(str, Enum):
    """Execution states for a planned operation."""

    PLANNED = "planned"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentSubtaskRole(str, Enum):
    """Internal roles used during planning and validation."""

    PLANNER = "planner"
    RESEARCHER = "researcher"
    WRITER = "writer"
    EDITOR = "editor"
    CONTINUITY = "continuity"


class AgentSubtaskStatus(str, Enum):
    """Execution states for internal subtasks."""

    PLANNED = "planned"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentPermissionLevel(str, Enum):
    """User-facing confirmation level for an operation."""

    READ_SEARCH = "read_search"
    STANDARD_WRITE = "standard_write"
    HIGH_RISK_WRITE = "high_risk_write"


class AgentRiskLevel(str, Enum):
    """Risk labels shown to users."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentVerificationStatus(str, Enum):
    """Verification states for operations and runs."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentThread(Base, UUIDMixin, TimestampMixin):
    """Project-scoped agent conversation thread."""

    __tablename__ = "agent_threads"
    __table_args__ = (UniqueConstraint("project_id", "is_default", name="unique_default_agent_thread"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), default="Primary Agent Workspace", nullable=False)
    is_default: Mapped[bool] = mapped_column(default=True, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, name="metadata")


class AgentMessage(Base, UUIDMixin, TimestampMixin):
    """Message history for an agent thread."""

    __tablename__ = "agent_messages"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, name="metadata")


class AgentRun(Base, UUIDMixin, TimestampMixin):
    """A single user request translated into an executable plan."""

    __tablename__ = "agent_runs"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    assistant_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    revision_of_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=AgentRunStatus.DRAFT.value, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=AgentVerificationStatus.PENDING.value,
        index=True,
    )
    verification_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, name="metadata")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    secondary_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentOperation(Base, UUIDMixin, TimestampMixin):
    """A single planned or executed tool call within a run."""

    __tablename__ = "agent_operations"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_display: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    preview: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    permission_level: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=AgentPermissionLevel.STANDARD_WRITE.value,
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AgentRiskLevel.MEDIUM.value,
    )
    requires_secondary_confirmation: Mapped[bool] = mapped_column(default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=AgentOperationStatus.PLANNED.value,
        index=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=AgentVerificationStatus.PENDING.value,
    )
    verification_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    persisted_content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentSubtask(Base, UUIDMixin, TimestampMixin):
    """Internal subtask records created for planner, writer, editor, and continuity roles."""

    __tablename__ = "agent_subtasks"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=AgentSubtaskStatus.PLANNED.value,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, name="metadata")


class AgentThreadCheckpoint(Base, UUIDMixin, TimestampMixin):
    """Compressed thread state used to keep long-running workspaces efficient."""

    __tablename__ = "agent_thread_checkpoints"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    thread_summary: Mapped[str] = mapped_column(Text, nullable=False)
    active_object_bundle: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    recent_run_digest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_context_characters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
