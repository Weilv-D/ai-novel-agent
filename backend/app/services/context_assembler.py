"""Context assembly helpers for quality-oriented agent planning."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.memory import VectorSearchRequest
from app.services.chapter import chapter_service, scene_service, volume_service
from app.services.character import character_service
from app.services.llm import llm_service
from app.services.memory import memory_service
from app.services.world_setting import world_setting_service

CHARACTER_CONTEXT_LIMIT = 20
WORLD_SETTING_CONTEXT_LIMIT = 20
VOLUME_CONTEXT_LIMIT = 20
CHAPTER_CONTEXT_LIMIT = 40
SCENE_CONTEXT_LIMIT = 20
MEMORY_CONTEXT_LIMIT = 8


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).strip().lower()


def _excerpt(value: str | None, *, length: int = 240) -> str | None:
    if not value:
        return None
    text = value.strip()
    if len(text) <= length:
        return text
    return f"{text[:length].rstrip()}…"


class ContextAssembler:
    """Assemble layered planning context without changing workflow semantics."""

    async def build_context(
        self,
        db: AsyncSession,
        *,
        project: Project,
        request_context: dict[str, Any],
        user_message: str,
        latest_checkpoint: Any | None = None,
        mode: str = "planning",
    ) -> dict[str, Any]:
        characters = await character_service.get_by_project(db, project_id=project.id, limit=CHARACTER_CONTEXT_LIMIT)
        world_settings = await world_setting_service.get_by_project(
            db,
            project_id=project.id,
            limit=WORLD_SETTING_CONTEXT_LIMIT,
        )
        volumes = await volume_service.get_by_project(db, project_id=project.id, limit=VOLUME_CONTEXT_LIMIT)
        chapters = await chapter_service.get_by_project(db, project_id=project.id, limit=CHAPTER_CONTEXT_LIMIT)

        matched_characters = self._match_named_objects(user_message=user_message, objects=characters, field_name="name")
        matched_world_settings = self._match_named_objects(
            user_message=user_message,
            objects=world_settings,
            field_name="name",
        )
        current_character = None
        current_world_setting = None

        character_id = request_context.get("character_id")
        if character_id:
            try:
                current_character = await character_service.get(db, id=uuid.UUID(str(character_id)))
            except Exception:
                current_character = None

        world_setting_id = request_context.get("world_setting_id")
        if world_setting_id:
            try:
                current_world_setting = await world_setting_service.get(db, id=uuid.UUID(str(world_setting_id)))
            except Exception:
                current_world_setting = None

        if current_character is not None and all(character.id != current_character.id for character in matched_characters):
            matched_characters = [current_character, *matched_characters]
        if current_world_setting is not None and all(
            setting.id != current_world_setting.id for setting in matched_world_settings
        ):
            matched_world_settings = [current_world_setting, *matched_world_settings]

        focus_context: dict[str, Any] = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "summary": project.summary,
                "story_outline": _excerpt(project.story_outline, length=500),
            }
        }
        working_context: dict[str, Any] = {
            "matched_characters": [
                {"id": str(character.id), "name": character.name, "role": character.role}
                for character in matched_characters
            ],
            "matched_world_settings": [
                {"id": str(setting.id), "name": setting.name, "category": setting.category}
                for setting in matched_world_settings
            ],
        }

        current_scene = None
        current_chapter = None
        current_volume = None
        current_scenes: list[dict[str, Any]] = []
        adjacent_scenes: list[dict[str, Any]] = []
        current_volume_chapters: list[dict[str, Any]] = []

        volume_id = request_context.get("volume_id")
        if volume_id:
            try:
                current_volume = await volume_service.get(db, id=uuid.UUID(str(volume_id)))
            except Exception:
                current_volume = None

        chapter_id = request_context.get("chapter_id")
        if chapter_id:
            try:
                current_chapter = await chapter_service.get(db, id=uuid.UUID(str(chapter_id)))
            except Exception:
                current_chapter = None

        scene_id = request_context.get("scene_id")
        if scene_id:
            try:
                current_scene = await scene_service.get(db, id=uuid.UUID(str(scene_id)))
            except Exception:
                current_scene = None

        if current_chapter is not None:
            chapter_scenes = await scene_service.get_by_chapter(db, chapter_id=current_chapter.id, limit=SCENE_CONTEXT_LIMIT)
            current_scenes = [
                {
                    "id": str(scene.id),
                    "scene_order": scene.scene_order,
                    "location": scene.location,
                    "content": _excerpt(scene.content, length=220),
                }
                for scene in chapter_scenes
            ]
            focus_context["chapter"] = {
                "id": str(current_chapter.id),
                "chapter_number": current_chapter.chapter_number,
                "title": current_chapter.title,
                "outline": current_chapter.outline,
                "content": _excerpt(current_chapter.content, length=400),
            }
            if current_chapter.volume_id is not None and current_volume is None:
                try:
                    current_volume = await volume_service.get(db, id=current_chapter.volume_id)
                except Exception:
                    current_volume = None

        if current_scene is not None:
            focus_context["scene"] = {
                "id": str(current_scene.id),
                "scene_order": current_scene.scene_order,
                "location": current_scene.location,
                "content": _excerpt(current_scene.content, length=400),
                "chapter_id": str(current_scene.chapter_id),
                "pov_character_id": str(current_scene.pov_character_id) if current_scene.pov_character_id else None,
            }
            sibling_scenes = await scene_service.get_by_chapter(db, chapter_id=current_scene.chapter_id, limit=SCENE_CONTEXT_LIMIT)
            adjacent_scenes = [
                {
                    "id": str(scene.id),
                    "scene_order": scene.scene_order,
                    "location": scene.location,
                }
                for scene in sibling_scenes
                if abs(scene.scene_order - current_scene.scene_order) <= 1 and scene.id != current_scene.id
            ]
            if current_chapter is None:
                try:
                    current_chapter = await chapter_service.get(db, id=current_scene.chapter_id)
                except Exception:
                    current_chapter = None

        if current_volume is not None:
            volume_chapters = await chapter_service.get_by_volume(db, volume_id=current_volume.id, limit=CHAPTER_CONTEXT_LIMIT)
            current_volume_chapters = [
                {
                    "id": str(chapter.id),
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "outline": _excerpt(chapter.outline, length=180),
                }
                for chapter in volume_chapters
            ]
            focus_context["volume"] = {
                "id": str(current_volume.id),
                "volume_number": current_volume.volume_number,
                "title": current_volume.title,
                "outline": _excerpt(current_volume.outline, length=300),
            }

        thread_context = {
            "request_context": request_context,
            "latest_checkpoint": (
                {
                    "id": str(latest_checkpoint.id),
                    "thread_summary": latest_checkpoint.thread_summary,
                    "recent_run_digest": latest_checkpoint.recent_run_digest,
                }
                if latest_checkpoint is not None
                else None
            ),
            "mode": mode,
        }

        memory_context = await self._build_memory_context(
            db,
            project_id=project.id,
            user_message=user_message,
            request_context=request_context,
            matched_characters=matched_characters,
            matched_world_settings=matched_world_settings,
        )

        context_data: dict[str, Any] = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "genre": project.genre,
                "summary": project.summary,
                "story_outline": project.story_outline,
                "notes": project.notes,
            },
            "current_project": {
                "id": str(project.id),
                "name": project.name,
                "summary": project.summary,
                "story_outline": project.story_outline,
            },
            "characters": [
                {"id": str(character.id), "name": character.name, "role": character.role}
                for character in characters
            ],
            "world_settings": [
                {"id": str(setting.id), "name": setting.name, "category": setting.category}
                for setting in world_settings
            ],
            "volumes": [
                {
                    "id": str(volume.id),
                    "volume_number": volume.volume_number,
                    "title": volume.title,
                    "outline": volume.outline,
                }
                for volume in volumes
            ],
            "chapters": [
                {
                    "id": str(chapter.id),
                    "volume_id": str(chapter.volume_id) if chapter.volume_id is not None else None,
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "outline": chapter.outline,
                }
                for chapter in chapters
            ],
            "request_context": request_context,
            "agent_profile_id": project.agent_profile_id,
            "agent_settings": project.agent_settings,
            "focus_context": focus_context,
            "working_context": {
                **working_context,
                "current_scenes": current_scenes,
                "adjacent_scenes": adjacent_scenes,
                "current_volume_chapters": current_volume_chapters,
            },
            "memory_context": memory_context,
            "thread_context": thread_context,
            "context_summary": {
                "matched_character_count": len(matched_characters),
                "matched_world_setting_count": len(matched_world_settings),
                "memory_fact_count": len(memory_context.get("facts", [])),
                "focus_keys": sorted(focus_context),
            },
        }

        if current_volume is not None:
            context_data["current_volume"] = {
                "id": str(current_volume.id),
                "volume_number": current_volume.volume_number,
                "title": current_volume.title,
                "outline": current_volume.outline,
                "notes": current_volume.notes,
            }
        if current_volume_chapters:
            context_data["current_volume_chapters"] = current_volume_chapters
        if current_chapter is not None:
            context_data["current_chapter"] = {
                "id": str(current_chapter.id),
                "volume_id": str(current_chapter.volume_id) if current_chapter.volume_id is not None else None,
                "chapter_number": current_chapter.chapter_number,
                "title": current_chapter.title,
                "outline": current_chapter.outline,
                "content": _excerpt(current_chapter.content, length=400),
            }
        if current_scene is not None:
            context_data["current_scene"] = focus_context["scene"]
        if current_scenes:
            context_data["current_scenes"] = current_scenes
        if matched_characters:
            first_character = matched_characters[0]
            context_data["current_character"] = {
                "id": str(first_character.id),
                "name": first_character.name,
                "role": first_character.role,
            }
            focus_context["character"] = {
                "id": str(first_character.id),
                "name": first_character.name,
                "role": first_character.role,
            }
        if matched_world_settings:
            first_setting = matched_world_settings[0]
            context_data["current_world_setting"] = {
                "id": str(first_setting.id),
                "name": first_setting.name,
                "category": first_setting.category,
            }
            focus_context["world_setting"] = {
                "id": str(first_setting.id),
                "name": first_setting.name,
                "category": first_setting.category,
            }
        if latest_checkpoint is not None:
            context_data["latest_checkpoint"] = thread_context["latest_checkpoint"]
        return context_data

    async def _build_memory_context(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        user_message: str,
        request_context: dict[str, Any],
        matched_characters: list[Any],
        matched_world_settings: list[Any],
    ) -> dict[str, Any]:
        if not user_message.strip():
            return {"facts": [], "summary": "无检索事实"}
        try:
            query_embedding = await llm_service.embed_single(user_message)
        except Exception:
            return {"facts": [], "summary": "embedding 不可用，跳过记忆检索"}

        matches, _ = await memory_service.search_by_embedding(
            db,
            project_id=project_id,
            search_params=VectorSearchRequest(
                query_embedding=query_embedding,
                limit=MEMORY_CONTEXT_LIMIT,
                threshold=0.55,
                memory_type=None,
                related_character_ids=[character.id for character in matched_characters],
                related_world_setting_ids=[setting.id for setting in matched_world_settings],
                scope={
                    key: uuid.UUID(str(value))
                    for key, value in request_context.items()
                    if key in {"chapter_id", "scene_id", "volume_id"} and value
                },
            ),
        )
        facts = [
            {
                "id": str(match["id"]),
                "memory_type": match["memory_type"],
                "content": _excerpt(str(match["content"]), length=200),
                "similarity": match["similarity"],
                "meta": match["meta"],
            }
            for match in matches
        ]
        summary = "未命中相关记忆" if not facts else f"命中 {len(facts)} 条相关记忆"
        return {"facts": facts, "summary": summary}

    def _match_named_objects(
        self,
        *,
        user_message: str,
        objects: list[Any],
        field_name: str,
    ) -> list[Any]:
        haystack = _normalize_text(user_message)
        if not haystack:
            return []
        matched: list[Any] = []
        seen_keys: set[str] = set()
        for obj in objects:
            raw_name = getattr(obj, field_name, None)
            if not raw_name:
                continue
            normalized_name = _normalize_text(str(raw_name))
            if not normalized_name or normalized_name not in haystack or normalized_name in seen_keys:
                continue
            seen_keys.add(normalized_name)
            matched.append(obj)
        return matched

    @staticmethod
    def context_fingerprint(context_data: dict[str, Any]) -> str:
        """Build a stable fingerprint for freshness checks."""
        focus_context = context_data.get("focus_context", {})
        working_context = context_data.get("working_context", {})
        memory_context = context_data.get("memory_context", {})
        payload = {
            "focus_context": focus_context,
            "working_context": {
                "matched_characters": working_context.get("matched_characters", []),
                "matched_world_settings": working_context.get("matched_world_settings", []),
                "current_scenes": working_context.get("current_scenes", []),
                "current_volume_chapters": working_context.get("current_volume_chapters", []),
            },
            "memory_ids": [item.get("id") for item in memory_context.get("facts", [])],
            "agent_settings": context_data.get("agent_settings", {}),
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


context_assembler = ContextAssembler()
