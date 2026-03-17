"""WorldSetting schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.types import CONTENT_MAX_LENGTH

# ============ Enums ============

WorldSettingCategoryLiteral = Literal[
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
]


# ============ Category Constants ============

class WorldSettingCategory:
    """World setting category constants."""

    MAGIC_SYSTEM = "magic_system"
    GEOGRAPHY = "geography"
    HISTORY = "history"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    CULTURE = "culture"
    RELIGION = "religion"
    ECONOMY = "economy"
    RULES = "rules"
    OTHER = "other"


class WorldSettingBase(BaseModel):
    """Base world setting schema."""

    category: WorldSettingCategoryLiteral = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    content: str | None = Field(None, max_length=CONTENT_MAX_LENGTH, description=f"World setting content, max {CONTENT_MAX_LENGTH} characters")
    meta: dict[str, Any] = Field(default_factory=dict)


class WorldSettingCreate(WorldSettingBase):
    """Schema for creating a world setting."""

    project_id: UUID


class WorldSettingUpdate(BaseModel):
    """Schema for updating a world setting."""

    category: WorldSettingCategoryLiteral | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = Field(None, max_length=CONTENT_MAX_LENGTH, description=f"World setting content, max {CONTENT_MAX_LENGTH} characters")
    meta: dict[str, Any] | None = Field(None)


class WorldSettingResponse(WorldSettingBase):
    """Schema for world setting response."""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
