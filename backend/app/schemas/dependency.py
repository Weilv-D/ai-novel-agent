"""Dependency schemas for impact analysis and relationship tracking."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ============ Enums ============

# Type literals for dependency sources and targets
DependencyEntityTypeLiteral = Literal[
    "project", "character", "world_setting", "volume", "chapter", "scene", "suggestion"
]

# Dependency type literals
DependencyTypeLiteral = Literal["references", "influences", "contains", "precedes"]

# Status constants for backward compatibility and convenience
class DependencyType:
    """Dependency type constants."""

    REFERENCES = "references"  # e.g., chapter references character
    INFLUENCES = "influences"  # e.g., setting influences character
    CONTAINS = "contains"  # e.g., volume contains chapter
    PRECEDES = "precedes"  # e.g., chapter precedes another chapter


# ============ Dependency Schemas ============


class DependencyBase(BaseModel):
    """Base dependency schema."""

    source_type: DependencyEntityTypeLiteral = Field(
        ..., description="Type of the source object"
    )
    source_id: UUID = Field(..., description="ID of the source object")
    target_type: DependencyEntityTypeLiteral = Field(
        ..., description="Type of the target object"
    )
    target_id: UUID = Field(..., description="ID of the target object")
    dependency_type: DependencyTypeLiteral | None = Field(
        None, description="Type of dependency relationship"
    )


class DependencyCreate(DependencyBase):
    """Schema for creating a dependency."""

    project_id: UUID


class DependencyUpdate(BaseModel):
    """Schema for updating a dependency.

    Note: Only dependency_type can be updated via PATCH.
    """

    dependency_type: DependencyTypeLiteral | None = None


class DependencyResponse(DependencyBase):
    """Schema for dependency response."""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============ Impact Analysis Schemas ============


class ImpactAnalysisRequest(BaseModel):
    """Schema for impact analysis request."""

    source_type: DependencyEntityTypeLiteral = Field(
        ..., description="Type of the source object being modified"
    )
    source_id: UUID = Field(..., description="ID of the source object being modified")


class ImpactDetail(BaseModel):
    """Detail of a single impact."""

    target_type: DependencyEntityTypeLiteral
    target_id: UUID
    dependency_type: DependencyTypeLiteral | None
    description: str | None = None


class ImpactAnalysisResponse(BaseModel):
    """Schema for impact analysis response."""

    source_type: DependencyEntityTypeLiteral
    source_id: UUID
    impacted_objects: list[ImpactDetail]
    total_count: int
    analysis_summary: str | None = None


class DependencyQueryRequest(BaseModel):
    """Schema for querying dependencies."""

    source_type: DependencyEntityTypeLiteral | None = None
    source_id: UUID | None = None
    target_type: DependencyEntityTypeLiteral | None = None
    target_id: UUID | None = None
    dependency_type: DependencyTypeLiteral | None = None
