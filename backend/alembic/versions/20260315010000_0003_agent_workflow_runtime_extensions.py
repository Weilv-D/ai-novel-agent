"""Extend agent workflow runtime metadata

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dialect_types() -> tuple[sa.types.TypeEngine, sa.types.TypeEngine, sa.sql.elements.TextClause]:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        return (
            postgresql.UUID(as_uuid=True),
            postgresql.JSON(),
            sa.text("now()"),
        )
    return (
        sa.String(36),
        sa.JSON(),
        sa.text("CURRENT_TIMESTAMP"),
    )


def upgrade() -> None:
    """Add subtask/checkpoint tables and verification/risk fields."""
    uuid_type, json_type, timestamp_default = _dialect_types()

    op.add_column(
        "agent_runs",
        sa.Column("verification_status", sa.String(length=40), nullable=False, server_default="pending"),
    )
    op.add_column("agent_runs", sa.Column("verification_summary", sa.Text(), nullable=True))
    op.add_column("agent_runs", sa.Column("secondary_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agent_runs_verification_status", "agent_runs", ["verification_status"])

    op.add_column(
        "agent_operations",
        sa.Column("permission_level", sa.String(length=40), nullable=False, server_default="standard_write"),
    )
    op.add_column(
        "agent_operations",
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
    )
    op.add_column(
        "agent_operations",
        sa.Column("requires_secondary_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "agent_operations",
        sa.Column("verification_status", sa.String(length=40), nullable=False, server_default="pending"),
    )
    op.add_column("agent_operations", sa.Column("verification_summary", sa.Text(), nullable=True))
    op.add_column("agent_operations", sa.Column("preview_content_hash", sa.String(length=128), nullable=True))
    op.add_column("agent_operations", sa.Column("persisted_content_hash", sa.String(length=128), nullable=True))

    op.create_table(
        "agent_subtasks",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("run_id", uuid_type, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="planned"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_subtasks_run_id", "agent_subtasks", ["run_id"])
    op.create_index("ix_agent_subtasks_role", "agent_subtasks", ["role"])
    op.create_index("ix_agent_subtasks_status", "agent_subtasks", ["status"])

    op.create_table(
        "agent_thread_checkpoints",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("thread_id", uuid_type, nullable=False),
        sa.Column("profile_id", sa.String(80), nullable=False),
        sa.Column("thread_summary", sa.Text(), nullable=False),
        sa.Column("active_object_bundle", json_type, nullable=False, server_default="{}"),
        sa.Column("recent_run_digest", json_type, nullable=False, server_default="{}"),
        sa.Column("source_message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_context_characters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["thread_id"], ["agent_threads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_thread_checkpoints_thread_id", "agent_thread_checkpoints", ["thread_id"])
    op.create_index("ix_agent_thread_checkpoints_profile_id", "agent_thread_checkpoints", ["profile_id"])


def downgrade() -> None:
    """Revert runtime metadata extension."""
    op.drop_index("ix_agent_thread_checkpoints_profile_id", table_name="agent_thread_checkpoints")
    op.drop_index("ix_agent_thread_checkpoints_thread_id", table_name="agent_thread_checkpoints")
    op.drop_table("agent_thread_checkpoints")

    op.drop_index("ix_agent_subtasks_status", table_name="agent_subtasks")
    op.drop_index("ix_agent_subtasks_role", table_name="agent_subtasks")
    op.drop_index("ix_agent_subtasks_run_id", table_name="agent_subtasks")
    op.drop_table("agent_subtasks")

    op.drop_column("agent_operations", "persisted_content_hash")
    op.drop_column("agent_operations", "preview_content_hash")
    op.drop_column("agent_operations", "verification_summary")
    op.drop_column("agent_operations", "verification_status")
    op.drop_column("agent_operations", "requires_secondary_confirmation")
    op.drop_column("agent_operations", "risk_level")
    op.drop_column("agent_operations", "permission_level")

    op.drop_index("ix_agent_runs_verification_status", table_name="agent_runs")
    op.drop_column("agent_runs", "secondary_confirmed_at")
    op.drop_column("agent_runs", "verification_summary")
    op.drop_column("agent_runs", "verification_status")
