"""Initial schema creation

Revision ID: 0001
Revises:
Create Date: 2026-03-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Import pgvector for VECTOR type support (with fallback for SQLite)
# This mirrors the approach in app/models/memory.py for SQLite compatibility
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all database tables."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Determine column types and defaults based on dialect
    # PostgreSQL: UUID, JSON, now()
    # SQLite: String(36) for UUID, JSON (mapped to TEXT), CURRENT_TIMESTAMP
    if dialect == "postgresql":
        uuid_type = postgresql.UUID(as_uuid=True)
        json_type = postgresql.JSON()
        timestamp_default = sa.text("now()")
    else:
        # SQLite compatibility
        uuid_type = sa.String(36)  # UUID stored as string
        json_type = sa.JSON()  # SQLite maps JSON to TEXT
        timestamp_default = sa.text("CURRENT_TIMESTAMP")

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("api_key_hash", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("genre", sa.String(100), nullable=True),
        sa.Column("target_audience", sa.String(100), nullable=True),
        sa.Column("target_word_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="drafting"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

    # Create characters table
    op.create_table(
        "characters",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("profile", json_type, nullable=False, server_default="{}"),
        sa.Column("relationships", json_type, nullable=False, server_default="{}"),
        sa.Column("arc_state", json_type, nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_characters_project_id", "characters", ["project_id"])

    # Create world_settings table
    op.create_table(
        "world_settings",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_world_settings_project_id", "world_settings", ["project_id"])
    op.create_index("ix_world_settings_category", "world_settings", ["category"])

    # Create volumes table
    op.create_table(
        "volumes",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("volume_number", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("outline", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_volumes_project_id", "volumes", ["project_id"])

    # Create chapters table
    op.create_table(
        "chapters",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("volume_id", uuid_type, nullable=True),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("outline", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["volume_id"], ["volumes.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("project_id", "volume_id", "chapter_number", name="unique_chapter_number"),
    )
    op.create_index("ix_chapters_project_id", "chapters", ["project_id"])

    # Create scenes table
    op.create_table(
        "scenes",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("chapter_id", uuid_type, nullable=False),
        sa.Column("scene_order", sa.Integer(), nullable=False),
        sa.Column("pov_character_id", uuid_type, nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pov_character_id"], ["characters.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_scenes_chapter_id", "scenes", ["chapter_id"])

    # Ensure pgvector extension is enabled (PostgreSQL only)
    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Determine the embedding column type based on dialect
    if PGVECTOR_AVAILABLE and dialect == "postgresql":
        embedding_type = Vector(1536)  # pgvector VECTOR type for 1536-dim embeddings
    else:
        # SQLite fallback: use TEXT to store JSON array
        embedding_type = sa.Text()

    # Create memories table with pgvector support
    # For PostgreSQL: use VECTOR type with pgvector extension
    # For SQLite: use TEXT as fallback (stores JSON array as string)
    op.create_table(
        "memories",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_memories_project_id", "memories", ["project_id"])
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"])

    # Create optional HNSW index for faster vector similarity search (PostgreSQL only)
    if dialect == "postgresql":
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_memories_embedding_cosine
            ON memories USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
        """)

    # Create suggestions table
    op.create_table(
        "suggestions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", uuid_type, nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("content", json_type, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("impact_analysis", json_type, nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_suggestions_project_id", "suggestions", ["project_id"])
    op.create_index("ix_suggestions_status", "suggestions", ["status"])

    # Create snapshots table
    op.create_table(
        "snapshots",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", uuid_type, nullable=False),
        sa.Column("data", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_snapshots_project_id", "snapshots", ["project_id"])

    # Create dependencies table
    op.create_table(
        "dependencies",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", uuid_type, nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", uuid_type, nullable=False),
        sa.Column("dependency_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "project_id", "source_type", "source_id", "target_type", "target_id", name="unique_dependency"
        ),
    )
    op.create_index("ix_dependencies_project_id", "dependencies", ["project_id"])


def downgrade() -> None:
    """Drop all database tables in reverse order."""
    op.drop_index("ix_dependencies_project_id", table_name="dependencies")
    op.drop_table("dependencies")

    op.drop_index("ix_snapshots_project_id", table_name="snapshots")
    op.drop_table("snapshots")

    op.drop_index("ix_suggestions_status", table_name="suggestions")
    op.drop_index("ix_suggestions_project_id", table_name="suggestions")
    op.drop_table("suggestions")

    # Drop vector index before dropping memories table (PostgreSQL only)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_memories_embedding_cosine")
    op.drop_index("ix_memories_memory_type", table_name="memories")
    op.drop_index("ix_memories_project_id", table_name="memories")
    op.drop_table("memories")

    op.drop_index("ix_scenes_chapter_id", table_name="scenes")
    op.drop_table("scenes")

    op.drop_index("ix_chapters_project_id", table_name="chapters")
    op.drop_table("chapters")

    op.drop_index("ix_volumes_project_id", table_name="volumes")
    op.drop_table("volumes")

    op.drop_index("ix_world_settings_category", table_name="world_settings")
    op.drop_index("ix_world_settings_project_id", table_name="world_settings")
    op.drop_table("world_settings")

    op.drop_index("ix_characters_project_id", table_name="characters")
    op.drop_table("characters")

    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
