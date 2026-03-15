"""Schemas for project package export/import."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectPackageManifest(BaseModel):
    """Manifest for a project package export."""

    package_version: str = Field(..., description="Package format version")
    exported_at: datetime = Field(..., description="Export timestamp")
    app_version: str = Field(..., description="Application version at export time")
    source_project_id: UUID = Field(..., description="Original project ID")
    source_project_name: str = Field(..., description="Original project name")
    agent_profile_id: str = Field(..., description="Agent profile ID used")
    embedding_dimension: int = Field(..., description="Embedding dimension used")


class ProjectImportWarning(BaseModel):
    """A warning generated during project import."""

    code: str = Field(..., description="Warning code")
    message: str = Field(..., description="Human-readable warning message")
    details: dict[str, Any] | None = Field(default=None, description="Additional details")


class ProjectImportResponse(BaseModel):
    """Response for project import operation."""

    project_id: UUID = Field(..., description="New project ID")
    project_name: str = Field(..., description="New project name")
    imported_counts: dict[str, int] = Field(
        ...,
        description="Counts of imported objects by type",
    )
    warnings: list[ProjectImportWarning] = Field(
        default_factory=list,
        description="Warnings generated during import",
    )


class ProjectBundle(BaseModel):
    """Complete project data bundle for export/import."""

    project: dict[str, Any] = Field(..., description="Project metadata")
    characters: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Character records",
    )
    world_settings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="World setting records",
    )
    volumes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Volume records",
    )
    chapters: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Chapter records",
    )
    scenes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Scene records",
    )
    dependencies: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Dependency records",
    )
    snapshots: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Snapshot records",
    )
    memories: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Memory records",
    )
