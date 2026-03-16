"""Add project story outline and normalize chapters into volumes

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-16

"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def _format_story_outline(summary: str | None, notes: str | None) -> str | None:
    summary_text = (summary or "").strip()
    notes_text = (notes or "").strip()
    if not summary_text and not notes_text:
        return None
    if summary_text and notes_text:
        return f"【项目简介】\n{summary_text}\n\n【补充备注】\n{notes_text}"
    return summary_text or notes_text


def upgrade() -> None:
    """Add story outline and backfill default volumes for legacy projects."""
    bind = op.get_bind()
    inspector = inspect(bind)
    uuid_type = _uuid_type()

    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    if "story_outline" not in project_columns:
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(sa.Column("story_outline", sa.Text(), nullable=True))

    projects = list(
        bind.execute(
            sa.text("SELECT id, summary, notes, story_outline FROM projects")
        ).mappings()
    )
    for project in projects:
        if not str(project.get("story_outline") or "").strip():
            next_outline = _format_story_outline(project.get("summary"), project.get("notes"))
            if next_outline:
                bind.execute(
                    sa.text("UPDATE projects SET story_outline = :story_outline WHERE id = :project_id"),
                    {"story_outline": next_outline, "project_id": project["id"]},
                )

    volume_table = sa.table(
        "volumes",
        sa.column("id", uuid_type),
        sa.column("project_id", uuid_type),
        sa.column("volume_number", sa.Integer()),
        sa.column("title", sa.String(length=255)),
        sa.column("outline", sa.Text()),
        sa.column("notes", sa.Text()),
    )

    projects_with_null_chapters = list(
        bind.execute(
            sa.text(
                """
                SELECT DISTINCT project_id
                FROM chapters
                WHERE volume_id IS NULL
                """
            )
        ).scalars()
    )

    for project_id in projects_with_null_chapters:
        next_volume_number = bind.execute(
            sa.text(
                """
                SELECT COALESCE(MAX(volume_number), 0) + 1
                FROM volumes
                WHERE project_id = :project_id
                """
            ),
            {"project_id": project_id},
        ).scalar_one()
        volume_id = str(uuid.uuid4()) if bind.dialect.name != "postgresql" else uuid.uuid4()
        bind.execute(
            volume_table.insert().values(
                id=volume_id,
                project_id=project_id,
                volume_number=int(next_volume_number),
                title=f"第{int(next_volume_number)}卷",
                outline="默认兼容卷，用于承接迁移前尚未归卷的章节。",
                notes="system:migrated_default_volume",
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE chapters
                SET volume_id = :volume_id
                WHERE project_id = :project_id
                  AND volume_id IS NULL
                """
            ),
            {"volume_id": volume_id, "project_id": project_id},
        )


def downgrade() -> None:
    """Remove story outline and undo migrated default volumes where possible."""
    bind = op.get_bind()

    migrated_volumes = list(
        bind.execute(
            sa.text(
                """
                SELECT id, project_id
                FROM volumes
                WHERE notes = 'system:migrated_default_volume'
                """
            )
        ).mappings()
    )
    for volume in migrated_volumes:
        bind.execute(
            sa.text(
                """
                UPDATE chapters
                SET volume_id = NULL
                WHERE project_id = :project_id
                  AND volume_id = :volume_id
                """
            ),
            {"project_id": volume["project_id"], "volume_id": volume["id"]},
        )
        bind.execute(
            sa.text("DELETE FROM volumes WHERE id = :volume_id"),
            {"volume_id": volume["id"]},
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("story_outline")
