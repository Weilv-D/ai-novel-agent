"""Timeline API routes."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.chapter import Chapter, Scene, Volume
from app.models.memory import Memory
from app.schemas.timeline import (
    TimelineChapterResponse,
    TimelineEventResponse,
    TimelineResponse,
    TimelineVolumeInfo,
)
from app.services.project import project_service

router = APIRouter(prefix="/projects", tags=["timeline"])

_CHAPTER_ID_KEYS = {"chapter_id", "chapterId", "chapter_uuid", "chapterUuid"}
_SCENE_ID_KEYS = {"scene_id", "sceneId", "scene_uuid", "sceneUuid"}
_VOLUME_ID_KEYS = {"volume_id", "volumeId", "volume_uuid", "volumeUuid"}
_CHAPTER_NUMBER_KEYS = {"chapter_number", "chapterNumber", "chapter_no", "chapterNo", "chapter"}
_SCENE_ORDER_KEYS = {"scene_order", "sceneOrder", "scene"}
_VOLUME_NUMBER_KEYS = {"volume_number", "volumeNumber", "volume"}
_TITLE_KEYS = {"title", "label", "event_title", "eventTitle", "event_name", "eventName", "name"}
_SUMMARY_KEYS = {"summary", "description", "note", "notes"}


def _truncate_text(value: str, max_length: int) -> str:
    """Return a compact single-line text preview."""
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 1].rstrip()}..."


def _unwrap_scalar(value: Any) -> Any:
    """Peel common wrapper structures used in loose JSON metadata."""
    current = value
    while isinstance(current, list) and current:
        current = current[0]
    if isinstance(current, dict):
        for key in ("id", "value", "uuid", "pk", "target_id", "object_id"):
            if key in current:
                current = current[key]
                break
    return current


def _find_first_value(value: Any, *, keys: set[str], depth: int = 0, max_depth: int = 4) -> Any | None:
    """Search nested dict/list metadata for the first matching key."""
    if depth > max_depth:
        return None
    if isinstance(value, dict):
        for key in keys:
            if key in value:
                return value[key]
        for nested in value.values():
            found = _find_first_value(nested, keys=keys, depth=depth + 1, max_depth=max_depth)
            if found is not None:
                return found
        return None
    if isinstance(value, list):
        for item in value:
            found = _find_first_value(item, keys=keys, depth=depth + 1, max_depth=max_depth)
            if found is not None:
                return found
    return None


def _coerce_uuid_value(value: Any, *, valid_ids: set[str]) -> str | None:
    """Normalize a metadata value into a known UUID string."""
    scalar = _unwrap_scalar(value)
    if scalar is None:
        return None
    candidate = str(scalar)
    if candidate in valid_ids:
        return candidate
    return None


def _coerce_int_value(value: Any) -> int | None:
    """Normalize a metadata value into an integer when possible."""
    scalar = _unwrap_scalar(value)
    if scalar is None or isinstance(scalar, bool):
        return None
    if isinstance(scalar, int):
        return scalar
    if isinstance(scalar, float):
        return int(scalar)
    if isinstance(scalar, str):
        stripped = scalar.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _extract_uuid_reference(meta: dict[str, Any], *, keys: set[str], valid_ids: set[str]) -> str | None:
    """Extract a known UUID reference from loose metadata."""
    return _coerce_uuid_value(_find_first_value(meta, keys=keys), valid_ids=valid_ids)


def _extract_int_reference(meta: dict[str, Any], *, keys: set[str]) -> int | None:
    """Extract an integer reference from loose metadata."""
    return _coerce_int_value(_find_first_value(meta, keys=keys))


def _extract_text(meta: dict[str, Any], *, keys: set[str]) -> str | None:
    """Extract a readable text field from loose metadata."""
    value = _unwrap_scalar(_find_first_value(meta, keys=keys))
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_chapter_reference(
    *,
    meta: dict[str, Any],
    scene_by_id: dict[str, Scene],
    chapter_by_id: dict[str, Chapter],
    chapters_by_number: dict[int, list[Chapter]],
    volume_number_by_id: dict[str, int | None],
) -> tuple[str | None, str | None, int | None]:
    """Resolve chapter and scene references from memory metadata."""
    chapter_id = _extract_uuid_reference(meta, keys=_CHAPTER_ID_KEYS, valid_ids=set(chapter_by_id))
    scene_id = _extract_uuid_reference(meta, keys=_SCENE_ID_KEYS, valid_ids=set(scene_by_id))
    scene_order = _extract_int_reference(meta, keys=_SCENE_ORDER_KEYS)

    if scene_id is not None:
        scene = scene_by_id[scene_id]
        chapter_id = str(scene.chapter_id)
        scene_order = scene.scene_order

    if chapter_id is not None:
        return chapter_id, scene_id, scene_order

    chapter_number = _extract_int_reference(meta, keys=_CHAPTER_NUMBER_KEYS)
    if chapter_number is None:
        return None, scene_id, scene_order

    candidates = list(chapters_by_number.get(chapter_number, []))
    volume_id = _extract_uuid_reference(meta, keys=_VOLUME_ID_KEYS, valid_ids=set(volume_number_by_id))
    if volume_id is not None:
        candidates = [candidate for candidate in candidates if str(candidate.volume_id) == volume_id]

    volume_number = _extract_int_reference(meta, keys=_VOLUME_NUMBER_KEYS)
    if volume_number is not None:
        candidates = [
            candidate
            for candidate in candidates
            if volume_number_by_id.get(str(candidate.volume_id)) == volume_number
        ]

    if len(candidates) != 1:
        return None, scene_id, scene_order

    chapter = candidates[0]
    if scene_id is None and scene_order is not None:
        return str(chapter.id), None, scene_order
    return str(chapter.id), None, scene_order


def _build_event_payload(
    *,
    memory: Memory,
    chapter: Chapter | None,
    scene: Scene | None,
    scene_order: int | None,
) -> TimelineEventResponse:
    """Build one timeline event response item."""
    meta = dict(memory.meta or {})
    title = _extract_text(meta, keys=_TITLE_KEYS) or _truncate_text(memory.content, 28)
    summary = _extract_text(meta, keys=_SUMMARY_KEYS) or _truncate_text(memory.content, 96)
    location = scene.location if scene else _extract_text(meta, keys={"location", "place"})

    return TimelineEventResponse(
        id=memory.id,
        memory_type=memory.memory_type,
        title=title,
        summary=summary,
        content=memory.content,
        meta=meta,
        chapter_id=chapter.id if chapter else None,
        chapter_number=chapter.chapter_number if chapter else None,
        chapter_title=chapter.title if chapter else None,
        scene_id=scene.id if scene else None,
        scene_order=scene.scene_order if scene else scene_order,
        location=location,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


@router.get("/{project_id}/timeline", response_model=TimelineResponse)
async def get_project_timeline(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
) -> TimelineResponse:
    """Aggregate ordered chapters with episode memories for timeline rendering."""
    await project_service.get(db, id=project_id)

    volumes_result = await db.execute(
        select(Volume).where(Volume.project_id == project_id).order_by(Volume.volume_number.asc(), Volume.created_at.asc())
    )
    volumes = list(volumes_result.scalars().all())

    chapters_result = await db.execute(
        select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.created_at.asc())
    )
    chapters = list(chapters_result.scalars().all())

    chapter_ids = [chapter.id for chapter in chapters]
    scenes: list[Scene] = []
    if chapter_ids:
        scenes_result = await db.execute(
            select(Scene)
            .where(Scene.chapter_id.in_(chapter_ids))
            .order_by(Scene.chapter_id.asc(), Scene.scene_order.asc(), Scene.created_at.asc())
        )
        scenes = list(scenes_result.scalars().all())

    memories_result = await db.execute(
        select(Memory)
        .where(Memory.project_id == project_id, Memory.memory_type == "episode")
        .order_by(Memory.created_at.asc(), Memory.updated_at.asc())
    )
    memories = list(memories_result.scalars().all())

    volume_by_id = {str(volume.id): volume for volume in volumes}
    volume_number_by_id = {str(volume.id): volume.volume_number for volume in volumes}
    chapter_by_id = {str(chapter.id): chapter for chapter in chapters}
    chapters_by_volume: dict[str | None, list[Chapter]] = defaultdict(list)
    chapters_by_number: dict[int, list[Chapter]] = defaultdict(list)
    for chapter in chapters:
        chapters_by_volume[str(chapter.volume_id) if chapter.volume_id else None].append(chapter)
        chapters_by_number[chapter.chapter_number].append(chapter)

    ordered_chapters: list[Chapter] = []
    for volume in volumes:
        ordered_chapters.extend(
            sorted(
                chapters_by_volume.get(str(volume.id), []),
                key=lambda chapter: (chapter.chapter_number, chapter.created_at),
            )
        )
    ordered_chapters.extend(
        sorted(
            chapters_by_volume.get(None, []),
            key=lambda chapter: (chapter.chapter_number, chapter.created_at),
        )
    )

    scene_by_id = {str(scene.id): scene for scene in scenes}
    scene_by_chapter_and_order = {
        (str(scene.chapter_id), scene.scene_order): scene
        for scene in scenes
    }

    events_by_chapter: dict[str, list[tuple[tuple[int, int, str], TimelineEventResponse]]] = defaultdict(list)
    unassigned_events: list[TimelineEventResponse] = []

    for memory in memories:
        meta = dict(memory.meta or {})
        chapter_id, scene_id, scene_order = _resolve_chapter_reference(
            meta=meta,
            scene_by_id=scene_by_id,
            chapter_by_id=chapter_by_id,
            chapters_by_number=chapters_by_number,
            volume_number_by_id=volume_number_by_id,
        )
        resolved_chapter = chapter_by_id.get(chapter_id) if chapter_id else None
        resolved_scene = scene_by_id.get(scene_id) if scene_id else None
        if resolved_scene is None and chapter_id is not None and scene_order is not None:
            resolved_scene = scene_by_chapter_and_order.get((chapter_id, scene_order))

        event_payload = _build_event_payload(
            memory=memory,
            chapter=resolved_chapter,
            scene=resolved_scene,
            scene_order=scene_order,
        )

        if resolved_chapter is None:
            unassigned_events.append(event_payload)
            continue

        order_key = (
            resolved_scene.scene_order if resolved_scene else (scene_order or 9999),
            int(memory.created_at.timestamp()),
            str(memory.id),
        )
        events_by_chapter[str(resolved_chapter.id)].append((order_key, event_payload))

    timeline_chapters = [
        TimelineChapterResponse(
            id=chapter.id,
            volume=(
                TimelineVolumeInfo(
                    id=volume_by_id[str(chapter.volume_id)].id,
                    volume_number=volume_by_id[str(chapter.volume_id)].volume_number,
                    title=volume_by_id[str(chapter.volume_id)].title,
                )
                if chapter.volume_id and str(chapter.volume_id) in volume_by_id
                else None
            ),
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            status=chapter.status,
            outline=chapter.outline,
            event_count=len(events_by_chapter.get(str(chapter.id), [])),
            events=[
                payload
                for _, payload in sorted(
                    events_by_chapter.get(str(chapter.id), []),
                    key=lambda item: item[0],
                )
            ],
            created_at=chapter.created_at,
            updated_at=chapter.updated_at,
        )
        for chapter in ordered_chapters
    ]

    return TimelineResponse(
        project_id=project_id,
        chapters=timeline_chapters,
        unassigned_events=sorted(unassigned_events, key=lambda event: (event.created_at, event.id)),
        total_events=sum(chapter.event_count for chapter in timeline_chapters) + len(unassigned_events),
    )
