"""Pydantic schemas for request/response validation."""

from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.character import CharacterCreate, CharacterResponse, CharacterUpdate
from app.schemas.world_setting import WorldSettingCreate, WorldSettingResponse, WorldSettingUpdate
from app.schemas.chapter import (
    VolumeCreate, VolumeResponse, VolumeUpdate,
    ChapterCreate, ChapterResponse, ChapterUpdate,
    SceneCreate, SceneResponse, SceneUpdate,
)
from app.schemas.suggestion import (
    SuggestionCreate, SuggestionResponse, SuggestionUpdate,
    SuggestionActionRequest, SuggestionActionResult,
)

__all__ = [
    "ProjectCreate",
    "ProjectResponse",
    "ProjectUpdate",
    "CharacterCreate",
    "CharacterResponse",
    "CharacterUpdate",
    "WorldSettingCreate",
    "WorldSettingResponse",
    "WorldSettingUpdate",
    "VolumeCreate",
    "VolumeResponse",
    "VolumeUpdate",
    "ChapterCreate",
    "ChapterResponse",
    "ChapterUpdate",
    "SceneCreate",
    "SceneResponse",
    "SceneUpdate",
    "SuggestionCreate",
    "SuggestionResponse",
    "SuggestionUpdate",
    "SuggestionActionRequest",
    "SuggestionActionResult",
]
