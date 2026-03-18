"""Structured text import service."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from time import time
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.exceptions import BadRequestException
from app.schemas.chapter import ChapterCreate, ChapterStatus, VolumeCreate
from app.schemas.character import CharacterCreate
from app.schemas.dependency import DependencyCreate, DependencyType
from app.schemas.memory import MemoryCreate, MemoryType
from app.schemas.project import ProjectCreate
from app.schemas.text_import import (
    DetectedChapter,
    DetectedCharacter,
    DetectedVolume,
    DetectedWorldSetting,
    TextImportPhaseLiteral,
    TextImportPreview,
    TextImportProgress,
    TextImportResponse,
)
from app.schemas.types import CONTENT_MAX_LENGTH
from app.schemas.world_setting import WorldSettingCategory, WorldSettingCreate
from app.services.chapter import chapter_service, volume_service
from app.services.character import character_service
from app.services.dependency import dependency_service
from app.services.llm import llm_service
from app.services.memory import memory_service
from app.services.project import project_service
from app.services.world_setting import world_setting_service

try:
    import chardet  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency at runtime
    chardet = None

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _ChapterMarker:
    chapter_number: int
    title: str | None
    line_index: int


@dataclass(slots=True)
class _VolumeMarker:
    volume_number: int
    title: str | None
    line_index: int


class TextImportService:
    """Analyze uploaded text and commit a structured project preview."""

    MAX_FILE_SIZE = 64 * 1024 * 1024
    MIN_CHAR_COUNT = 500
    CHAPTER_OUTLINE_MAX_CHARS = 12000
    CHAPTER_OUTLINE_BATCH_SIZE = 4
    MAX_STORED_CHAPTER_CHARS = min(CONTENT_MAX_LENGTH, 480000)
    ENTITY_GROUP_SIZE = 5
    ENTITY_EXTRACTION_BATCH_SIZE = 3
    ENTITY_GROUP_LIMIT = 24
    ENTITY_SAMPLE_LIMIT = 60000
    ENTITY_GROUP_SAMPLE_CHARS = 8000
    ENTITY_RETRY_SAMPLE_CHARS = 2500
    LLM_TEXT_TIMEOUT_SECONDS = 20
    LLM_JSON_TIMEOUT_SECONDS = 60
    PREVIEW_CACHE_TTL_SECONDS = 3600
    MAX_INLINE_PREVIEW_CHARS = 200000
    CHAPTER_PREVIEW_CONTENT_CHARS = 400
    SUMMARY_GROUP_SIZE = 12
    SUMMARY_DIGEST_TARGET_CHARS = 16000
    CHARACTER_COOCCURRENCE_MIN_CHAPTERS = 2
    CHAPTER_MEMORY_SUMMARY_CHARS = 240
    CHAPTER_MEMORY_CONTENT_CHARS = 600
    DEPENDENCY_SAMPLE_CHARS = 2400

    _CHAPTER_HEADING_RE = re.compile(
        r"^\s*(?:第(?P<cn_num>[零〇一二两三四五六七八九十百千\d]+)(?P<cn_unit>[章节回集篇部])|chapter\s+(?P<en_num>\d+))"
        r"(?:\s*[：:、.\-]\s*|\s+)?(?P<title>.*)$",
        re.IGNORECASE,
    )
    _VOLUME_HEADING_RE = re.compile(
        r"^\s*(?:第(?P<cn_num>[零〇一二两三四五六七八九十百千\d]+)卷|卷(?P<cn_num_alt>[零〇一二两三四五六七八九十百千\d]+)|volume\s+(?P<en_num>\d+))"
        r"(?:\s*[：:、.\-]\s*|\s+)?(?P<title>.*)$",
        re.IGNORECASE,
    )
    _MARKDOWN_CHAPTER_RE = re.compile(r"^\s*##+\s+(?P<title>.+?)\s*$")
    _MARKDOWN_VOLUME_RE = re.compile(r"^\s*#\s+(?P<title>.+?)\s*$")
    _CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

    def __init__(self) -> None:
        self.llm = llm_service
        self._preview_store: dict[str, tuple[float, dict[str, Any]]] = {}

    def _preview_cache_key(self, preview_id: str) -> str:
        """Build a stable cache key for stored import previews."""
        return f"text-import-preview:{preview_id}"

    def _prune_preview_store(self) -> None:
        """Remove expired locally cached previews."""
        now = time()
        expired = [preview_id for preview_id, (expires_at, _) in self._preview_store.items() if expires_at <= now]
        for preview_id in expired:
            self._preview_store.pop(preview_id, None)

    async def _store_preview_snapshot(self, preview: TextImportPreview) -> str:
        """Persist a preview snapshot for later confirmation."""
        self._prune_preview_store()
        preview_id = uuid4().hex
        payload = preview.model_dump(mode="json")
        expires_at = time() + self.PREVIEW_CACHE_TTL_SECONDS
        self._preview_store[preview_id] = (expires_at, payload)
        await cache_service.set(
            self._preview_cache_key(preview_id),
            payload,
            ttl=self.PREVIEW_CACHE_TTL_SECONDS,
        )
        return preview_id

    async def _load_preview_snapshot(self, preview_id: str) -> TextImportPreview | None:
        """Load a previously stored preview snapshot."""
        self._prune_preview_store()
        local_payload = self._preview_store.get(preview_id)
        if local_payload is not None:
            expires_at, payload = local_payload
            if expires_at > time():
                return TextImportPreview.model_validate(payload)
            self._preview_store.pop(preview_id, None)

        cached_payload = await cache_service.get(self._preview_cache_key(preview_id))
        if not isinstance(cached_payload, dict):
            return None
        return TextImportPreview.model_validate(cached_payload)

    async def _delete_preview_snapshot(self, preview_id: str | None) -> None:
        """Delete a stored preview snapshot."""
        if not preview_id:
            return
        self._preview_store.pop(preview_id, None)
        await cache_service.delete(self._preview_cache_key(preview_id))

    def decode_bytes(self, file_bytes: bytes) -> tuple[str, str]:
        """Decode uploaded text bytes using UTF-8 first, then common CJK encodings."""
        tried: list[str] = []
        for encoding in ("utf-8", "utf-8-sig"):
            try:
                return file_bytes.decode(encoding), encoding
            except UnicodeDecodeError:
                tried.append(encoding)

        detected_encoding: str | None = None
        if chardet is not None:
            detection = chardet.detect(file_bytes)
            candidate = detection.get("encoding")
            if isinstance(candidate, str) and candidate.strip():
                detected_encoding = candidate.strip()

        candidates: list[str | None] = [detected_encoding, "gb18030", "gbk", "gb2312", "big5"]
        for fallback_encoding in candidates:
            if not fallback_encoding or fallback_encoding in tried:
                continue
            try:
                return file_bytes.decode(fallback_encoding), fallback_encoding
            except UnicodeDecodeError:
                tried.append(fallback_encoding)

        raise BadRequestException("无法识别文件编码，请确认上传的是有效的 TXT 或 Markdown 文本")

    async def analyze(
        self,
        text: str,
        project_name: str,
        genre: str | None = None,
        *,
        source_filename: str | None = None,
        source_encoding: str | None = None,
    ) -> AsyncIterator[TextImportProgress]:
        """Analyze uploaded text and stream progress events."""
        normalized_text = self._normalize_text(text)
        preview = TextImportPreview(
            project_name=project_name.strip() or "未命名项目",
            genre=self._clean_optional_text(genre),
            source_filename=source_filename,
            source_encoding=source_encoding,
        )

        yield TextImportProgress(
            phase="structure_detection",
            progress=0.02,
            message="正在识别章节与卷结构",
        )

        chapters = self._split_chapters(normalized_text)
        volumes = self._detect_volumes(normalized_text, chapters)
        preview.chapters, preview.volumes = self._normalize_detected_structure(chapters, volumes, preview)
        if len(chapters) == 1:
            self._append_warning(preview, "未检测到稳定章节标记，已按单章导入。")

        yield TextImportProgress(
            phase="structure_detection",
            progress=0.15,
            message=f"已识别 {len(preview.volumes)} 个卷 / {len(chapters)} 个章节",
            data={
                "volumes": len(preview.volumes),
                "chapters": len(preview.chapters),
                "warnings": list(preview.warnings),
            },
        )

        outline_warnings = 0
        total_chapters = max(len(preview.chapters), 1)
        for start in range(0, len(preview.chapters), self.CHAPTER_OUTLINE_BATCH_SIZE):
            batch = preview.chapters[start : start + self.CHAPTER_OUTLINE_BATCH_SIZE]
            results = await asyncio.gather(
                *(self._generate_chapter_outline(chapter) for chapter in batch),
            )
            for chapter, outline in zip(batch, results, strict=True):
                if outline.used_fallback:
                    outline_warnings += 1
                chapter.outline = outline.content
            completed = start + len(batch)
            yield TextImportProgress(
                phase="outline_extraction",
                progress=0.15 + 0.40 * (completed / total_chapters),
                message=f"已生成 {completed}/{len(preview.chapters)} 个章纲",
            )

        if outline_warnings:
            self._append_warning(preview, f"{outline_warnings} 个章纲使用了启发式摘要兜底。")

        summary_result = await self._generate_project_summary(
            preview.chapters,
            project_name=preview.project_name,
            genre=preview.genre,
        )
        preview.summary = summary_result["summary"]
        preview.story_outline = summary_result["story_outline"]
        preview.genre = summary_result["genre"]
        if summary_result["used_fallback"]:
            self._append_warning(preview, "项目摘要与总纲未能完整调用 LLM，已使用启发式摘要兜底。")

        generated_volume_outlines = await self._generate_volume_outlines(preview.volumes, preview.chapters)
        for volume, volume_outline in zip(preview.volumes, generated_volume_outlines, strict=True):
            volume.outline = volume_outline

        yield TextImportProgress(
            phase="outline_extraction",
            progress=0.60,
            message="已完成大纲与卷纲提取",
            data={
                "summary_ready": bool(preview.summary),
                "story_outline_ready": bool(preview.story_outline),
            },
        )

        if self._will_sample_entity_groups(preview.chapters):
            self._append_warning(preview, "文本体量较大，角色与世界观抽取已启用代表章节采样。")

        try:
            preview.characters = await self._extract_characters(preview.chapters)
            yield TextImportProgress(
                phase="character_extraction",
                progress=0.80,
                message=f"已提取 {len(preview.characters)} 个角色",
                data={"characters": len(preview.characters)},
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Character extraction failed: %s", exc)
            preview.characters = []
            self._mark_phase_failed(preview, "character_extraction", "角色提取失败，已跳过该阶段。")
            yield TextImportProgress(
                phase="character_extraction",
                progress=0.80,
                message="角色提取失败，已跳过",
                data={"warnings": list(preview.warnings)},
            )

        try:
            preview.world_settings = await self._extract_world_settings(preview.chapters)
            yield TextImportProgress(
                phase="world_setting_extraction",
                progress=0.95,
                message=f"已提取 {len(preview.world_settings)} 个世界观设定",
                data={"world_settings": len(preview.world_settings)},
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("World setting extraction failed: %s", exc)
            preview.world_settings = []
            self._mark_phase_failed(preview, "world_setting_extraction", "世界观提取失败，已跳过该阶段。")
            yield TextImportProgress(
                phase="world_setting_extraction",
                progress=0.95,
                message="世界观提取失败，已跳过",
                data={"warnings": list(preview.warnings)},
            )

        client_preview = await self._build_client_preview(preview)

        yield TextImportProgress(
            phase="completed",
            progress=1.0,
            message="分析完成，请预览后确认导入",
            data={"preview": client_preview.model_dump(mode="json")},
        )

    async def commit(
        self,
        db: AsyncSession,
        preview: TextImportPreview,
    ) -> TextImportResponse:
        """Create project data from a confirmed text-import preview."""
        resolved_preview = preview
        stored_preview: TextImportPreview | None = None
        if preview.preview_id:
            stored_preview = await self._load_preview_snapshot(preview.preview_id)
            if stored_preview is None and preview.compact_preview:
                raise BadRequestException("导入预览已过期，请重新分析后再确认导入")
            if stored_preview is not None:
                resolved_preview = self._merge_confirmed_preview(stored_preview, preview)

        project = await project_service.create_project(
            db,
            obj_in=ProjectCreate(
                name=resolved_preview.project_name,
                genre=self._clean_optional_text(resolved_preview.genre),
                summary=self._clean_optional_text(resolved_preview.summary),
                story_outline=self._clean_optional_text(resolved_preview.story_outline),
            ),
        )

        imported_counts: dict[str, int] = {"projects": 1}
        chapter_to_volume_id: dict[int, Any] = {}
        chapter_to_volume_number: dict[int, int] = {}
        volume_records = resolved_preview.volumes or self._build_default_volumes(resolved_preview.chapters)
        created_volumes_by_number: dict[int, Any] = {}

        for volume in sorted(volume_records, key=lambda item: item.volume_number):
            created_volume = await volume_service.create_with_project(
                db,
                obj_in=VolumeCreate(
                    project_id=project.id,
                    volume_number=volume.volume_number,
                    title=self._clean_optional_text(volume.title),
                    outline=self._clean_optional_text(volume.outline),
                ),
                project_id=project.id,
            )
            created_volumes_by_number[volume.volume_number] = created_volume
            for chapter_number in volume.chapter_numbers:
                chapter_to_volume_id[chapter_number] = created_volume.id
                chapter_to_volume_number[chapter_number] = volume.volume_number
            imported_counts["volumes"] = imported_counts.get("volumes", 0) + 1

        created_chapters: list[tuple[DetectedChapter, Any]] = []
        for index, chapter in enumerate(resolved_preview.chapters, start=1):
            chapter_number = chapter.chapter_number or index
            created_chapter = await chapter_service.create_with_project(
                db,
                obj_in=ChapterCreate(
                    project_id=project.id,
                    volume_id=chapter_to_volume_id.get(chapter_number),
                    chapter_number=chapter_number,
                    title=self._clean_optional_text(chapter.title),
                    outline=self._clean_optional_text(chapter.outline),
                    content=chapter.content,
                    status=ChapterStatus.DRAFT,
                ),
                project_id=project.id,
            )
            created_chapters.append((chapter, created_chapter))
            imported_counts["chapters"] = imported_counts.get("chapters", 0) + 1

        created_characters_by_name: dict[str, Any] = {}
        for character in resolved_preview.characters:
            created_character = await character_service.create_with_project(
                db,
                obj_in=CharacterCreate(
                    project_id=project.id,
                    name=character.name,
                    role=self._clean_optional_text(character.role),
                    profile=character.profile,
                    relationships=character.relationships,
                ),
                project_id=project.id,
            )
            created_characters_by_name[character.name] = created_character
            imported_counts["characters"] = imported_counts.get("characters", 0) + 1

        created_world_settings_by_name: dict[str, Any] = {}
        for world_setting in resolved_preview.world_settings:
            created_world_setting = await world_setting_service.create_with_project(
                db,
                obj_in=WorldSettingCreate(
                    project_id=project.id,
                    category=world_setting.category,
                    name=world_setting.name,
                    content=world_setting.content,
                ),
                project_id=project.id,
            )
            created_world_settings_by_name[world_setting.name] = created_world_setting
            imported_counts["world_settings"] = imported_counts.get("world_settings", 0) + 1

        for detected_chapter, created_chapter in created_chapters:
            await memory_service.create_with_project(
                db,
                obj_in=MemoryCreate(
                    project_id=project.id,
                    memory_type=MemoryType.EPISODE,
                    content=self._build_import_memory_content(detected_chapter),
                    meta={
                        "title": detected_chapter.title or f"第{created_chapter.chapter_number}章",
                        "summary": detected_chapter.outline or self._sample_text(detected_chapter.content, self.CHAPTER_MEMORY_SUMMARY_CHARS),
                        "chapter_id": str(created_chapter.id),
                        "chapter_number": created_chapter.chapter_number,
                        "volume_id": str(created_chapter.volume_id) if created_chapter.volume_id else None,
                        "volume_number": chapter_to_volume_number.get(created_chapter.chapter_number),
                        "source": "text_import",
                    },
                ),
                project_id=project.id,
            )
            imported_counts["memories"] = imported_counts.get("memories", 0) + 1

        dependency_creates = self._build_import_dependency_creates(
            project_id=project.id,
            resolved_preview=resolved_preview,
            created_volumes_by_number=created_volumes_by_number,
            created_chapters=created_chapters,
            created_characters_by_name=created_characters_by_name,
            created_world_settings_by_name=created_world_settings_by_name,
        )
        for dependency_create in dependency_creates:
            await dependency_service.create_with_project(
                db,
                obj_in=dependency_create,
                project_id=project.id,
            )
            imported_counts["dependencies"] = imported_counts.get("dependencies", 0) + 1

        await db.commit()
        await self._delete_preview_snapshot(resolved_preview.preview_id)

        return TextImportResponse(
            project_id=project.id,
            project_name=project.name,
            imported_counts=imported_counts,
        )

    def _build_import_memory_content(self, chapter: DetectedChapter) -> str:
        """Build a compact episode-memory payload for an imported chapter."""
        return chapter.outline or self._sample_text(chapter.content, self.CHAPTER_MEMORY_CONTENT_CHARS)

    def _build_import_dependency_creates(
        self,
        *,
        project_id: Any,
        resolved_preview: TextImportPreview,
        created_volumes_by_number: dict[int, Any],
        created_chapters: Sequence[tuple[DetectedChapter, Any]],
        created_characters_by_name: dict[str, Any],
        created_world_settings_by_name: dict[str, Any],
    ) -> list[DependencyCreate]:
        """Derive baseline structural and reference dependencies for an imported project."""
        edges: set[tuple[str, Any, str, Any, str]] = set()

        for volume in resolved_preview.volumes:
            created_volume = created_volumes_by_number.get(volume.volume_number)
            if created_volume is None:
                continue
            edges.add(("project", project_id, "volume", created_volume.id, DependencyType.CONTAINS))

        for created_character in created_characters_by_name.values():
            edges.add(("project", project_id, "character", created_character.id, DependencyType.CONTAINS))

        for created_world_setting in created_world_settings_by_name.values():
            edges.add(("project", project_id, "world_setting", created_world_setting.id, DependencyType.CONTAINS))

        created_chapter_by_number = {
            detected_chapter.chapter_number: created_chapter
            for detected_chapter, created_chapter in created_chapters
        }
        for volume in resolved_preview.volumes:
            created_volume = created_volumes_by_number.get(volume.volume_number)
            if created_volume is None:
                continue
            for chapter_number in volume.chapter_numbers:
                created_chapter = created_chapter_by_number.get(chapter_number)
                if created_chapter is None:
                    continue
                edges.add(("volume", created_volume.id, "chapter", created_chapter.id, DependencyType.CONTAINS))

        for index in range(len(created_chapters) - 1):
            _, source_chapter = created_chapters[index]
            _, target_chapter = created_chapters[index + 1]
            edges.add(("chapter", source_chapter.id, "chapter", target_chapter.id, DependencyType.PRECEDES))

        lowered_character_names = {
            name: created_character.id
            for name, created_character in created_characters_by_name.items()
        }
        lowered_world_setting_names = {
            name: created_world_setting.id
            for name, created_world_setting in created_world_settings_by_name.items()
        }

        for detected_chapter, created_chapter in created_chapters:
            haystack = self._chapter_reference_haystack(detected_chapter, max_chars=self.DEPENDENCY_SAMPLE_CHARS)
            for name, character_id in lowered_character_names.items():
                if name.casefold() in haystack:
                    edges.add(("chapter", created_chapter.id, "character", character_id, DependencyType.REFERENCES))
            for name, world_setting_id in lowered_world_setting_names.items():
                if name.casefold() in haystack:
                    edges.add(("chapter", created_chapter.id, "world_setting", world_setting_id, DependencyType.REFERENCES))

        return [
            DependencyCreate(
                project_id=project_id,
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                dependency_type=dependency_type,
            )
            for source_type, source_id, target_type, target_id, dependency_type in sorted(
                edges,
                key=lambda item: (item[0], str(item[1]), item[2], str(item[3]), item[4]),
            )
        ]

    def _normalize_detected_structure(
        self,
        chapters: Sequence[DetectedChapter],
        volumes: Sequence[DetectedVolume],
        preview: TextImportPreview,
    ) -> tuple[list[DetectedChapter], list[DetectedVolume]]:
        """Ensure chapter payloads remain storable and volume mappings stay aligned."""
        normalized_chapters: list[DetectedChapter] = []
        chapter_number_map: dict[int, list[int]] = {}
        split_chapter_count = 0
        next_chapter_number = 1

        for chapter in chapters:
            parts = self._split_content_for_storage(chapter.content, max_chars=self.MAX_STORED_CHAPTER_CHARS)
            chapter_number_map[chapter.chapter_number] = []
            if len(parts) > 1:
                split_chapter_count += 1

            for index, part in enumerate(parts, start=1):
                title = chapter.title
                if len(parts) > 1:
                    title = self._build_chapter_part_title(chapter.title, index, len(parts))
                normalized_chapters.append(
                    DetectedChapter(
                        chapter_number=next_chapter_number,
                        title=title,
                        content=part,
                        outline=chapter.outline if index == 1 else None,
                        content_length=len(part),
                        content_truncated=False,
                    )
                )
                chapter_number_map[chapter.chapter_number].append(next_chapter_number)
                next_chapter_number += 1

        normalized_volumes: list[DetectedVolume] = []
        for volume in volumes:
            expanded_numbers: list[int] = []
            for chapter_number in volume.chapter_numbers:
                expanded_numbers.extend(chapter_number_map.get(chapter_number, []))
            if not expanded_numbers:
                continue
            normalized_volumes.append(
                volume.model_copy(
                    update={"chapter_numbers": expanded_numbers}
                )
            )

        if split_chapter_count:
            self._append_warning(
                preview,
                f"{split_chapter_count} 个超长章节已自动拆分为可安全存储的多段章节。",
            )

        if not normalized_volumes:
            normalized_volumes = self._build_default_volumes(normalized_chapters)

        return normalized_chapters, normalized_volumes

    def _split_content_for_storage(self, content: str, *, max_chars: int) -> list[str]:
        """Split oversized chapter content into storage-safe sections."""
        normalized = content.strip()
        if not normalized:
            return [""]
        if len(normalized) <= max_chars:
            return [normalized]

        paragraphs = [segment.strip() for segment in normalized.split("\n\n") if segment.strip()]
        if not paragraphs:
            return self._chunk_text(normalized, max_chars=max_chars, overlap=0)

        parts: list[str] = []
        current: list[str] = []
        for paragraph in paragraphs:
            candidate = "\n\n".join([*current, paragraph]) if current else paragraph
            if len(candidate) <= max_chars:
                current.append(paragraph)
                continue

            if current:
                parts.append("\n\n".join(current))
                current = []

            if len(paragraph) <= max_chars:
                current = [paragraph]
                continue

            parts.extend(self._chunk_text(paragraph, max_chars=max_chars, overlap=0))

        if current:
            parts.append("\n\n".join(current))

        return [part for part in parts if part.strip()]

    def _build_chapter_part_title(self, title: str | None, index: int, total: int) -> str:
        """Build a readable title for a split chapter fragment."""
        base_title = self._clean_optional_text(title) or "导入正文"
        return f"{base_title}（{index}/{total}）"

    def _estimate_preview_chars(self, preview: TextImportPreview) -> int:
        """Estimate the serialized weight of a preview."""
        total = len(preview.project_name) + len(preview.genre or "") + len(preview.summary or "") + len(preview.story_outline or "")
        total += sum(len(warning) for warning in preview.warnings)
        total += sum(len(chapter.title or "") + len(chapter.outline or "") + len(chapter.content) for chapter in preview.chapters)
        total += sum(len(volume.title or "") + len(volume.outline or "") for volume in preview.volumes)
        total += sum(len(character.name) + len(character.role or "") for character in preview.characters)
        total += sum(len(setting.name) + len(setting.content) for setting in preview.world_settings)
        return total

    async def _build_client_preview(self, preview: TextImportPreview) -> TextImportPreview:
        """Store the full preview and return a client-safe snapshot."""
        preview_id = await self._store_preview_snapshot(preview)
        client_preview = preview.model_copy(deep=True)
        client_preview.preview_id = preview_id

        if self._estimate_preview_chars(preview) <= self.MAX_INLINE_PREVIEW_CHARS:
            for chapter in client_preview.chapters:
                chapter.content_length = len(chapter.content)
                chapter.content_truncated = False
            return client_preview

        client_preview.compact_preview = True
        self._append_warning(
            client_preview,
            "文本体量较大，预览中的正文仅展示节选；确认导入时仍会保留完整原文。",
        )
        for chapter in client_preview.chapters:
            chapter.content_length = len(chapter.content)
            if len(chapter.content) <= self.CHAPTER_PREVIEW_CONTENT_CHARS:
                chapter.content_truncated = False
                continue
            chapter.content = self._sample_text(chapter.content, self.CHAPTER_PREVIEW_CONTENT_CHARS)
            chapter.content_truncated = True
        return client_preview

    def _merge_confirmed_preview(
        self,
        stored_preview: TextImportPreview,
        edited_preview: TextImportPreview,
    ) -> TextImportPreview:
        """Merge editable preview fields back onto the full stored preview snapshot."""
        merged_preview = stored_preview.model_copy(deep=True)
        merged_preview.preview_id = edited_preview.preview_id
        merged_preview.compact_preview = False
        merged_preview.project_name = edited_preview.project_name
        merged_preview.genre = self._clean_optional_text(edited_preview.genre)
        merged_preview.summary = self._clean_optional_text(edited_preview.summary)
        merged_preview.story_outline = self._clean_optional_text(edited_preview.story_outline)

        stored_volumes = {volume.volume_number: volume for volume in stored_preview.volumes}
        merged_preview.volumes = [
            stored_volumes.get(volume.volume_number, volume).model_copy(
                update={
                    "title": self._clean_optional_text(volume.title),
                    "outline": self._clean_optional_text(volume.outline),
                    "chapter_numbers": list(volume.chapter_numbers),
                }
            )
            for volume in edited_preview.volumes
        ]

        stored_chapters = {chapter.chapter_number: chapter for chapter in stored_preview.chapters}
        merged_chapters: list[DetectedChapter] = []
        for chapter in edited_preview.chapters:
            stored_chapter = stored_chapters.get(chapter.chapter_number)
            content = chapter.content
            if stored_chapter is not None and chapter.content_truncated:
                content = stored_chapter.content
            merged_chapters.append(
                DetectedChapter(
                    chapter_number=chapter.chapter_number,
                    title=self._clean_optional_text(chapter.title),
                    outline=self._clean_optional_text(chapter.outline),
                    content=content,
                    content_length=len(content),
                    content_truncated=False,
                )
            )
        merged_preview.chapters = merged_chapters
        merged_preview.characters = list(edited_preview.characters)
        merged_preview.world_settings = list(edited_preview.world_settings)
        merged_preview.warnings = list(dict.fromkeys([*stored_preview.warnings, *edited_preview.warnings]))
        merged_preview.failed_phases = list(dict.fromkeys([*stored_preview.failed_phases, *edited_preview.failed_phases]))
        return merged_preview

    def _split_chapters(self, text: str) -> list[DetectedChapter]:
        """Split raw text into chapter previews using heading heuristics."""
        lines = text.splitlines()
        chapter_markers, _ = self._scan_structure(lines)
        if not chapter_markers:
            return [
                DetectedChapter(
                    chapter_number=1,
                    title="导入正文",
                    content=text.strip(),
                    outline=None,
                    content_length=len(text.strip()),
                    content_truncated=False,
                )
            ]

        chapters: list[DetectedChapter] = []
        for index, marker in enumerate(chapter_markers):
            next_line_index = chapter_markers[index + 1].line_index if index + 1 < len(chapter_markers) else len(lines)
            raw_content = "\n".join(lines[marker.line_index + 1 : next_line_index]).strip()
            title = self._clean_optional_text(marker.title) or f"第{marker.chapter_number}章"
            content = raw_content or title
            chapters.append(
                DetectedChapter(
                    chapter_number=marker.chapter_number,
                    title=title,
                    content=content,
                    outline=None,
                    content_length=len(content),
                    content_truncated=False,
                )
            )
        return chapters

    def _detect_volumes(self, text: str, chapters: Sequence[DetectedChapter]) -> list[DetectedVolume]:
        """Detect volume grouping for chapters. Falls back to a single default volume."""
        if not chapters:
            return []

        lines = text.splitlines()
        chapter_markers, volume_markers = self._scan_structure(lines)
        if not volume_markers:
            return self._build_default_volumes(chapters)

        chapter_to_line = {
            marker.chapter_number: marker.line_index
            for marker in chapter_markers
        }
        volumes: list[DetectedVolume] = []
        for index, volume_marker in enumerate(volume_markers):
            next_volume_line = volume_markers[index + 1].line_index if index + 1 < len(volume_markers) else None
            chapter_numbers = [
                chapter.chapter_number
                for chapter in chapters
                if chapter_to_line.get(chapter.chapter_number) is not None
                and chapter_to_line[chapter.chapter_number] > volume_marker.line_index
                and (next_volume_line is None or chapter_to_line[chapter.chapter_number] < next_volume_line)
            ]
            if not chapter_numbers:
                continue
            volumes.append(
                DetectedVolume(
                    volume_number=volume_marker.volume_number,
                    title=self._clean_optional_text(volume_marker.title) or f"第{volume_marker.volume_number}卷",
                    outline=None,
                    chapter_numbers=chapter_numbers,
                )
            )

        return volumes or self._build_default_volumes(chapters)

    async def _generate_chapter_outline(self, chapter: DetectedChapter) -> _OutlineResult:
        """Generate a short outline for a chapter, with heuristic fallback."""
        if not self._llm_ready():
            return _OutlineResult(self._fallback_chapter_outline(chapter), True)

        try:
            chapter_text = chapter.content
            if len(chapter_text) > self.CHAPTER_OUTLINE_MAX_CHARS:
                chunk_summaries = await asyncio.gather(
                    *(self._summarize_chunk(chunk) for chunk in self._chunk_text(chapter_text))
                )
                chapter_text = "\n".join(chunk_summaries)

            response = await asyncio.wait_for(
                self.llm.generate(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是中文长篇小说编辑。请根据章节原文写一段 100 到 200 字的中文章纲，"
                            "突出人物、冲突、推进和结果，只返回章纲正文。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"章节标题：{chapter.title or f'第{chapter.chapter_number}章'}\n\n"
                            f"章节正文：\n{chapter_text}"
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=500,
                ),
                timeout=self.LLM_TEXT_TIMEOUT_SECONDS,
            )
            content = self._clean_optional_text(response["content"])
            if content:
                return _OutlineResult(content, False)
        except Exception as exc:  # pragma: no cover - LLM/network failures
            logger.warning("Chapter outline generation failed for chapter %s: %s", chapter.chapter_number, exc)

        return _OutlineResult(self._fallback_chapter_outline(chapter), True)

    async def _generate_project_summary(
        self,
        chapters: Sequence[DetectedChapter],
        *,
        project_name: str,
        genre: str | None,
    ) -> dict[str, Any]:
        """Generate project-level summary, outline, and genre."""
        if not chapters:
            return {
                "summary": None,
                "story_outline": None,
                "genre": genre,
                "used_fallback": True,
            }

        outline_block, digest_used_fallback = await self._prepare_outline_digest(chapters, label="故事阶段")
        if self._llm_ready():
            try:
                payload = await self._generate_json_payload(
                    [
                        {
                            "role": "system",
                            "content": (
                                "你是中文小说策划编辑。请基于多个章纲提炼项目简介、项目总纲，并推断题材。"
                                "只返回 JSON 对象，字段为 summary、story_outline、genre。"
                            ),
                        },
                        {
                            "role": "user",
                        "content": (
                            f"项目名：{project_name}\n"
                            f"当前题材（可为空）：{genre or '未提供'}\n\n"
                            f"章纲摘要：\n{outline_block}"
                        ),
                    },
                ],
                    expect="object",
                )
                summary = self._clean_optional_text(str(payload.get("summary") or ""))
                story_outline = self._clean_optional_text(str(payload.get("story_outline") or ""))
                detected_genre = self._clean_optional_text(str(payload.get("genre") or "")) or genre
                if summary or story_outline:
                    return {
                        "summary": summary,
                        "story_outline": story_outline or summary,
                        "genre": detected_genre,
                        "used_fallback": digest_used_fallback,
                    }
            except Exception as exc:  # pragma: no cover - LLM/network failures
                logger.warning("Project summary generation failed: %s", exc)

        summary = self._fallback_project_summary(chapters)
        return {
            "summary": summary,
            "story_outline": self._fallback_story_outline(chapters),
            "genre": genre or "未分类",
            "used_fallback": True,
        }

    async def _extract_characters(self, chapters: Sequence[DetectedChapter]) -> list[DetectedCharacter]:
        """Extract key characters from chapter outlines and samples."""
        if not chapters or not self._llm_ready():
            return []

        groups = self._select_entity_groups(self._build_entity_groups(chapters))
        candidates: list[DetectedCharacter] = []
        failures: list[BaseException] = []
        for start in range(0, len(groups), self.ENTITY_EXTRACTION_BATCH_SIZE):
            batch = groups[start : start + self.ENTITY_EXTRACTION_BATCH_SIZE]
            results = await asyncio.gather(
                *(self._extract_character_group(group) for group in batch),
                return_exceptions=True,
            )
            for group, result in zip(batch, results, strict=True):
                if isinstance(result, BaseException):
                    logger.warning("Character extraction subgroup failed: %s", result)
                    try:
                        fallback_result = await self._extract_character_group(
                            group,
                            include_text_sample=False,
                            max_characters=5,
                            sample_chars=self.ENTITY_RETRY_SAMPLE_CHARS,
                            max_tokens=900,
                        )
                    except Exception as retry_exc:
                        logger.warning("Character extraction subgroup retry failed: %s", retry_exc)
                        failures.append(retry_exc)
                    else:
                        candidates.extend(fallback_result)
                    continue
                candidates.extend(result)

        if not candidates:
            outline_candidates = await self._extract_characters_from_outline_digest(chapters)
            if outline_candidates:
                return self._backfill_character_relationships(self._merge_characters(outline_candidates)[:20], chapters)
            if failures:
                raise failures[0]
            return []

        return self._backfill_character_relationships(self._merge_characters(candidates)[:20], chapters)

    async def _extract_world_settings(self, chapters: Sequence[DetectedChapter]) -> list[DetectedWorldSetting]:
        """Extract key world settings from chapter outlines and samples."""
        if not chapters or not self._llm_ready():
            return []

        categories = ", ".join(
            [
                WorldSettingCategory.MAGIC_SYSTEM,
                WorldSettingCategory.GEOGRAPHY,
                WorldSettingCategory.HISTORY,
                WorldSettingCategory.ORGANIZATION,
                WorldSettingCategory.TECHNOLOGY,
                WorldSettingCategory.CULTURE,
                WorldSettingCategory.RELIGION,
                WorldSettingCategory.ECONOMY,
                WorldSettingCategory.RULES,
                WorldSettingCategory.OTHER,
            ]
        )
        groups = self._select_entity_groups(self._build_entity_groups(chapters))
        candidates: list[DetectedWorldSetting] = []
        failures: list[BaseException] = []
        for start in range(0, len(groups), self.ENTITY_EXTRACTION_BATCH_SIZE):
            batch = groups[start : start + self.ENTITY_EXTRACTION_BATCH_SIZE]
            results = await asyncio.gather(
                *(self._extract_world_setting_group(group, categories) for group in batch),
                return_exceptions=True,
            )
            for group, result in zip(batch, results, strict=True):
                if isinstance(result, BaseException):
                    logger.warning("World-setting extraction subgroup failed: %s", result)
                    try:
                        fallback_result = await self._extract_world_setting_group(
                            group,
                            categories,
                            include_text_sample=False,
                            max_items=4,
                            sample_chars=self.ENTITY_RETRY_SAMPLE_CHARS,
                            max_tokens=900,
                        )
                    except Exception as retry_exc:
                        logger.warning("World-setting extraction subgroup retry failed: %s", retry_exc)
                        failures.append(retry_exc)
                    else:
                        candidates.extend(fallback_result)
                    continue
                candidates.extend(result)

        if not candidates:
            outline_candidates = await self._extract_world_settings_from_outline_digest(chapters, categories)
            if outline_candidates:
                return self._merge_world_settings(outline_candidates)[:15]
            if failures:
                raise failures[0]
            return []

        return self._merge_world_settings(candidates)[:15]

    async def _extract_character_group(
        self,
        chapters: Sequence[DetectedChapter],
        *,
        include_text_sample: bool = True,
        max_characters: int = 8,
        sample_chars: int | None = None,
        max_tokens: int = 1200,
    ) -> list[DetectedCharacter]:
        """Extract character candidates for a single chapter group."""
        prompt_sections = [f"章纲：\n{self._build_outline_block(chapters)}"]
        if include_text_sample:
            prompt_sections.append(
                f"原文采样：\n{self._build_text_sample(chapters, max_chars=sample_chars or self.ENTITY_GROUP_SAMPLE_CHARS)}"
            )
        payload = await self._generate_json_payload(
            [
                {
                    "role": "system",
                    "content": (
                        "你是中文小说人物策划编辑。请从提供的章纲和原文采样中提取关键角色，"
                        "只返回 JSON 数组。每个元素字段为 name、role、profile、relationships。"
                        f"profile 和 relationships 必须是 JSON 对象。不要返回超过 {max_characters} 个角色。"
                    ),
                },
                {
                    "role": "user",
                    "content": "\n\n".join(prompt_sections),
                },
            ],
            expect="array",
            max_tokens=max_tokens,
        )
        return self._normalize_detected_characters(payload)

    async def _extract_world_setting_group(
        self,
        chapters: Sequence[DetectedChapter],
        categories: str,
        *,
        include_text_sample: bool = True,
        max_items: int = 6,
        sample_chars: int | None = None,
        max_tokens: int = 1200,
    ) -> list[DetectedWorldSetting]:
        """Extract world-setting candidates for a single chapter group."""
        prompt_sections = [f"章纲：\n{self._build_outline_block(chapters)}"]
        if include_text_sample:
            prompt_sections.append(
                f"原文采样：\n{self._build_text_sample(chapters, max_chars=sample_chars or self.ENTITY_GROUP_SAMPLE_CHARS)}"
            )
        payload = await self._generate_json_payload(
            [
                {
                    "role": "system",
                    "content": (
                        "你是中文小说世界观策划编辑。请从提供的章纲和原文采样中提取关键设定，"
                        "只返回 JSON 数组。每个元素字段为 category、name、content。"
                        f"category 必须从以下枚举中选择：{categories}。不要返回超过 {max_items} 个设定。"
                    ),
                },
                {
                    "role": "user",
                    "content": "\n\n".join(prompt_sections),
                },
            ],
            expect="array",
            max_tokens=max_tokens,
        )
        return self._normalize_detected_world_settings(payload)

    def _chunk_text(self, text: str, max_chars: int = 12000, overlap: int = 500) -> list[str]:
        """Split long text into overlapping chunks."""
        normalized = text.strip()
        if not normalized:
            return []
        if len(normalized) <= max_chars:
            return [normalized]

        chunks: list[str] = []
        start = 0
        step = max(max_chars - overlap, 1)
        while start < len(normalized):
            end = min(start + max_chars, len(normalized))
            chunks.append(normalized[start:end])
            if end >= len(normalized):
                break
            start += step
        return chunks

    async def _summarize_chunk(self, chunk: str) -> str:
        """Summarize a chunk from a long chapter."""
        if not self._llm_ready():
            return self._sample_text(chunk, 320)

        try:
            response = await asyncio.wait_for(
                self.llm.generate(
                [
                    {
                        "role": "system",
                        "content": "请把这段中文小说正文压缩为不超过 120 字的摘要，只返回摘要正文。",
                    },
                    {"role": "user", "content": chunk},
                ],
                temperature=0.2,
                max_tokens=240,
                ),
                timeout=self.LLM_TEXT_TIMEOUT_SECONDS,
            )
            content = self._clean_optional_text(response["content"])
            if content:
                return content
        except Exception as exc:  # pragma: no cover - LLM/network failures
            logger.warning("Chunk summary generation failed: %s", exc)
        return self._sample_text(chunk, 320)

    async def _generate_volume_outlines(
        self,
        volumes: Sequence[DetectedVolume],
        chapters: Sequence[DetectedChapter],
    ) -> list[str | None]:
        """Generate or derive volume outlines from grouped chapter outlines."""
        chapter_map = {chapter.chapter_number: chapter for chapter in chapters}
        outlines: list[str | None] = []
        for volume in volumes:
            scoped = [chapter_map[number] for number in volume.chapter_numbers if number in chapter_map]
            if not scoped:
                outlines.append(None)
                continue
            outline_block, _ = await self._prepare_outline_digest(scoped, label=f"{volume.title or f'第{volume.volume_number}卷'}阶段")
            if self._llm_ready():
                try:
                    response = await asyncio.wait_for(
                        self.llm.generate(
                        [
                            {
                                "role": "system",
                                "content": "你是中文长篇小说策划编辑。请根据卷内章纲写一段不超过 220 字的卷纲，只返回卷纲正文。",
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"卷名：{volume.title or f'第{volume.volume_number}卷'}\n\n"
                                    f"卷内章纲摘要：\n{outline_block}"
                                ),
                            },
                        ],
                        temperature=0.2,
                        max_tokens=380,
                        ),
                        timeout=self.LLM_TEXT_TIMEOUT_SECONDS,
                    )
                    content = self._clean_optional_text(response["content"])
                    if content:
                        outlines.append(content)
                        continue
                except Exception as exc:  # pragma: no cover - LLM/network failures
                    logger.warning("Volume outline generation failed for volume %s: %s", volume.volume_number, exc)
            outlines.append(self._fallback_volume_outline(volume, scoped))
        return outlines

    def _scan_structure(self, lines: Sequence[str]) -> tuple[list[_ChapterMarker], list[_VolumeMarker]]:
        """Scan all lines for chapter and volume markers."""
        has_markdown_chapters = any(self._MARKDOWN_CHAPTER_RE.match(line) for line in lines)
        chapter_markers: list[_ChapterMarker] = []
        volume_markers: list[_VolumeMarker] = []
        next_chapter_number = 1
        next_volume_number = 1
        used_chapter_numbers: set[int] = set()
        used_volume_numbers: set[int] = set()

        for line_index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            volume_match = self._match_volume_heading(stripped, has_markdown_chapters)
            if volume_match is not None:
                parsed_volume_number = volume_match["number"]
                if parsed_volume_number is None or parsed_volume_number in used_volume_numbers:
                    volume_number = next_volume_number
                else:
                    volume_number = parsed_volume_number
                used_volume_numbers.add(volume_number)
                next_volume_number = max(next_volume_number, volume_number + 1)
                volume_markers.append(
                    _VolumeMarker(
                        volume_number=volume_number,
                        title=volume_match["title"],
                        line_index=line_index,
                    )
                )
                continue

            chapter_match = self._match_chapter_heading(stripped)
            if chapter_match is not None:
                parsed_chapter_number = chapter_match["number"]
                if (
                    parsed_chapter_number is None
                    or parsed_chapter_number in used_chapter_numbers
                    or parsed_chapter_number < next_chapter_number
                ):
                    chapter_number = next_chapter_number
                else:
                    chapter_number = parsed_chapter_number
                used_chapter_numbers.add(chapter_number)
                next_chapter_number = max(next_chapter_number, chapter_number + 1)
                chapter_markers.append(
                    _ChapterMarker(
                        chapter_number=chapter_number,
                        title=chapter_match["title"],
                        line_index=line_index,
                    )
                )

        return chapter_markers, volume_markers

    def _match_chapter_heading(self, line: str) -> dict[str, Any] | None:
        """Match a line as a chapter heading."""
        chapter_match = self._CHAPTER_HEADING_RE.match(line)
        if chapter_match:
            number = self._parse_heading_number(
                chapter_match.group("cn_num") or chapter_match.group("en_num")
            )
            title = self._clean_optional_text(chapter_match.group("title")) or line.strip()
            return {
                "number": number,
                "title": title,
            }

        markdown_match = self._MARKDOWN_CHAPTER_RE.match(line)
        if markdown_match:
            return {
                "number": None,
                "title": self._clean_optional_text(markdown_match.group("title")),
            }
        return None

    def _match_volume_heading(self, line: str, allow_markdown: bool) -> dict[str, Any] | None:
        """Match a line as a volume heading."""
        volume_match = self._VOLUME_HEADING_RE.match(line)
        if volume_match:
            number = self._parse_heading_number(
                volume_match.group("cn_num")
                or volume_match.group("cn_num_alt")
                or volume_match.group("en_num")
            )
            title = self._clean_optional_text(volume_match.group("title")) or line.strip()
            return {
                "number": number,
                "title": title,
            }

        if allow_markdown:
            markdown_match = self._MARKDOWN_VOLUME_RE.match(line)
            if markdown_match:
                markdown_title = self._clean_optional_text(markdown_match.group("title"))
                if markdown_title:
                    return {"number": None, "title": markdown_title}
        return None

    def _parse_heading_number(self, value: str | None) -> int | None:
        """Parse Arabic or Chinese numerals from heading markers."""
        if not value:
            return None
        if value.isdigit():
            return int(value)

        numerals = {
            "零": 0,
            "〇": 0,
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
        }
        units = {"十": 10, "百": 100, "千": 1000}

        total = 0
        current = 0
        unit = 1
        for char in reversed(value):
            if char in numerals:
                current += numerals[char] * unit
            elif char in units:
                if current == 0:
                    current = 1
                total += current * units[char]
                current = 0
                unit = 1
            else:
                return None
        return total + current if total + current > 0 else None

    def _build_default_volumes(self, chapters: Sequence[DetectedChapter]) -> list[DetectedVolume]:
        """Build a single fallback volume when no explicit volume structure is found."""
        if not chapters:
            return []
        return [
            DetectedVolume(
                volume_number=1,
                title="第一卷",
                outline=None,
                chapter_numbers=[chapter.chapter_number for chapter in chapters],
            )
        ]

    def _normalize_text(self, text: str) -> str:
        """Normalize line endings and strip zero-width garbage."""
        return (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\ufeff", "")
            .replace("\u200b", "")
            .strip()
        )

    def _clean_optional_text(self, value: str | None) -> str | None:
        """Trim optional text values."""
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def _llm_ready(self) -> bool:
        """Return whether the configured LLM client is available."""
        return bool(self.llm.api_key)

    def _append_warning(self, preview: TextImportPreview, message: str) -> None:
        """Append a warning only once."""
        if message not in preview.warnings:
            preview.warnings.append(message)

    def _mark_phase_failed(
        self,
        preview: TextImportPreview,
        phase: TextImportPhaseLiteral,
        warning: str,
    ) -> None:
        """Record a failed phase without duplicating markers."""
        if phase not in preview.failed_phases:
            preview.failed_phases.append(phase)
        self._append_warning(preview, warning)

    def _fallback_chapter_outline(self, chapter: DetectedChapter) -> str:
        """Build a deterministic fallback outline from chapter content."""
        snippet = self._sample_text(chapter.content, 180)
        title = chapter.title or f"第{chapter.chapter_number}章"
        return f"{title}：{snippet}"

    def _fallback_project_summary(self, chapters: Sequence[DetectedChapter]) -> str:
        """Build a short fallback project summary."""
        first_outline = chapters[0].outline or self._fallback_chapter_outline(chapters[0])
        last_outline = chapters[-1].outline or self._fallback_chapter_outline(chapters[-1])
        if len(chapters) == 1:
            return self._sample_text(first_outline, 180)
        return self._sample_text(f"故事从{first_outline}展开，并推进至{last_outline}", 220)

    def _fallback_story_outline(self, chapters: Sequence[DetectedChapter]) -> str:
        """Build a fallback project outline from chapter outlines."""
        lines = []
        for chapter in chapters[:12]:
            outline = chapter.outline or self._fallback_chapter_outline(chapter)
            lines.append(f"第{chapter.chapter_number}章 {chapter.title or '未命名'}：{outline}")
        return "\n".join(lines)

    def _fallback_volume_outline(
        self,
        volume: DetectedVolume,
        chapters: Sequence[DetectedChapter],
    ) -> str:
        """Build a fallback volume outline from chapter outlines."""
        scope = [
            chapter.outline or self._fallback_chapter_outline(chapter)
            for chapter in chapters[:6]
        ]
        return self._sample_text(
            f"{volume.title or f'第{volume.volume_number}卷'}聚焦：" + "；".join(scope),
            240,
        )

    def _sample_text(self, text: str, max_chars: int) -> str:
        """Sample long text using head/middle/tail windows."""
        normalized = self._normalize_text(text)
        if len(normalized) <= max_chars:
            return normalized
        segment = max(max_chars // 3, 40)
        middle_start = max((len(normalized) // 2) - (segment // 2), 0)
        tail_start = max(len(normalized) - segment, 0)
        return (
            f"{normalized[:segment]}\n...\n"
            f"{normalized[middle_start:middle_start + segment]}\n...\n"
            f"{normalized[tail_start:]}"
        )

    def _render_outline_lines(self, chapters: Sequence[DetectedChapter]) -> list[str]:
        """Render outline lines for a chapter collection."""
        return [
            f"第{chapter.chapter_number}章 {chapter.title or '未命名'}：{chapter.outline or self._fallback_chapter_outline(chapter)}"
            for chapter in chapters
        ]

    def _build_outline_block(self, chapters: Sequence[DetectedChapter]) -> str:
        """Render chapter outlines for prompting."""
        return "\n".join(self._render_outline_lines(chapters))

    def _build_text_sample(self, chapters: Sequence[DetectedChapter], *, max_chars: int) -> str:
        """Build balanced source-text samples from first/middle/last chapters."""
        if not chapters:
            return ""
        pivot_indexes = sorted({0, len(chapters) // 2, len(chapters) - 1})
        per_section = max(max_chars // max(len(pivot_indexes), 1), 500)
        sections = []
        for index in pivot_indexes:
            chapter = chapters[index]
            sections.append(
                f"[第{chapter.chapter_number}章 {chapter.title or '未命名'}]\n{self._sample_text(chapter.content, per_section)}"
            )
        return "\n\n".join(sections)[:max_chars]

    async def _extract_characters_from_outline_digest(
        self,
        chapters: Sequence[DetectedChapter],
    ) -> list[DetectedCharacter]:
        """Fallback character extraction using only compressed outline material."""
        if not chapters or not self._llm_ready():
            return []

        try:
            outline_block, _ = await self._prepare_outline_digest(chapters, label="人物阶段")
            payload = await self._generate_json_payload(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是中文小说人物策划编辑。请只根据故事阶段摘要提取关键角色，"
                            "只返回 JSON 数组。每个元素字段为 name、role、profile、relationships。"
                            "profile 和 relationships 可以为空对象，不要返回超过 12 个角色。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"故事阶段摘要：\n{outline_block}",
                    },
                ],
                expect="array",
                max_tokens=900,
            )
        except Exception as exc:  # pragma: no cover - network/model failures
            logger.warning("Outline-only character extraction failed: %s", exc)
            return []
        return self._normalize_detected_characters(payload)

    async def _extract_world_settings_from_outline_digest(
        self,
        chapters: Sequence[DetectedChapter],
        categories: str,
    ) -> list[DetectedWorldSetting]:
        """Fallback world-setting extraction using only compressed outline material."""
        if not chapters or not self._llm_ready():
            return []

        try:
            outline_block, _ = await self._prepare_outline_digest(chapters, label="设定阶段")
            payload = await self._generate_json_payload(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是中文小说世界观策划编辑。请只根据故事阶段摘要提取关键设定，"
                            "只返回 JSON 数组。每个元素字段为 category、name、content。"
                            f"category 必须从以下枚举中选择：{categories}。不要返回超过 10 个设定。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"故事阶段摘要：\n{outline_block}",
                    },
                ],
                expect="array",
                max_tokens=900,
            )
        except Exception as exc:  # pragma: no cover - network/model failures
            logger.warning("Outline-only world-setting extraction failed: %s", exc)
            return []
        return self._normalize_detected_world_settings(payload)

    def _chapter_reference_haystack(self, chapter: DetectedChapter, *, max_chars: int) -> str:
        """Build a compact normalized text block for entity matching."""
        return self._normalize_text(
            "\n".join(
                part
                for part in [
                    chapter.title or "",
                    chapter.outline or "",
                    self._sample_text(chapter.content, max_chars),
                ]
                if part
            )
        ).casefold()

    def _backfill_character_relationships(
        self,
        characters: Sequence[DetectedCharacter],
        chapters: Sequence[DetectedChapter],
    ) -> list[DetectedCharacter]:
        """Infer lightweight co-occurrence relationships when extraction omits them."""
        if len(characters) < 2 or not chapters:
            return list(characters)

        pair_counts: Counter[tuple[str, str]] = Counter()
        character_names = [character.name for character in characters if character.name]
        lowered_names = {name: name.casefold() for name in character_names}

        for chapter in chapters:
            haystack = self._chapter_reference_haystack(chapter, max_chars=self.DEPENDENCY_SAMPLE_CHARS)
            mentioned = sorted({name for name, lowered in lowered_names.items() if lowered in haystack})
            if len(mentioned) < 2:
                continue
            for index, source_name in enumerate(mentioned):
                for target_name in mentioned[index + 1 :]:
                    pair_counts[(source_name, target_name)] += 1

        if not pair_counts:
            return list(characters)

        enriched: list[DetectedCharacter] = []
        for character in characters:
            relationships = dict(character.relationships)
            for (left_name, right_name), count in pair_counts.items():
                if count < self.CHARACTER_COOCCURRENCE_MIN_CHAPTERS:
                    continue
                label = "频繁共现" if count >= 3 else "同章出现"
                if character.name == left_name and right_name not in relationships:
                    relationships[right_name] = label
                elif character.name == right_name and left_name not in relationships:
                    relationships[left_name] = label
            enriched.append(character.model_copy(update={"relationships": relationships}))
        return enriched

    def _build_entity_groups(self, chapters: Sequence[DetectedChapter]) -> list[list[DetectedChapter]]:
        """Group chapters for entity extraction prompts."""
        return [list(chapters[index : index + self.ENTITY_GROUP_SIZE]) for index in range(0, len(chapters), self.ENTITY_GROUP_SIZE)]

    def _will_sample_entity_groups(self, chapters: Sequence[DetectedChapter]) -> bool:
        """Whether entity extraction will sample chapter groups for scale control."""
        return len(self._build_entity_groups(chapters)) > self.ENTITY_GROUP_LIMIT

    def _select_entity_groups(self, groups: Sequence[list[DetectedChapter]]) -> list[list[DetectedChapter]]:
        """Select representative entity groups when the novel is very large."""
        if len(groups) <= self.ENTITY_GROUP_LIMIT:
            return list(groups)

        if self.ENTITY_GROUP_LIMIT <= 1:
            return [list(groups[0])]

        selected_indexes: set[int] = set()
        max_index = len(groups) - 1
        for position in range(self.ENTITY_GROUP_LIMIT):
            raw_index = round((max_index * position) / (self.ENTITY_GROUP_LIMIT - 1))
            selected_indexes.add(raw_index)
        return [list(groups[index]) for index in sorted(selected_indexes)]

    async def _prepare_outline_digest(
        self,
        chapters: Sequence[DetectedChapter],
        *,
        label: str,
    ) -> tuple[str, bool]:
        """Reduce outline material to a prompt-safe digest."""
        items = self._render_outline_lines(chapters)
        used_fallback = False

        while items and (
            len("\n".join(items)) > self.SUMMARY_DIGEST_TARGET_CHARS
            or len(items) > self.SUMMARY_GROUP_SIZE
        ):
            next_items: list[str] = []
            for start in range(0, len(items), self.SUMMARY_GROUP_SIZE):
                group = items[start : start + self.SUMMARY_GROUP_SIZE]
                summary, fallback_used = await self._summarize_outline_group(
                    group,
                    label=f"{label}{start // self.SUMMARY_GROUP_SIZE + 1}",
                )
                used_fallback = used_fallback or fallback_used
                next_items.append(summary)
            items = next_items

        return "\n".join(items), used_fallback

    async def _summarize_outline_group(self, lines: Sequence[str], *, label: str) -> tuple[str, bool]:
        """Summarize a block of outline lines into a shorter digest."""
        source = "\n".join(lines)
        if not source:
            return "", False

        if not self._llm_ready():
            return self._sample_text(source, 500), True

        try:
            response = await asyncio.wait_for(
                self.llm.generate(
                    [
                        {
                            "role": "system",
                            "content": "你是中文小说策划编辑。请将一组章节章纲压缩为一段不超过 360 字的阶段摘要，只返回摘要正文。",
                        },
                        {
                            "role": "user",
                            "content": f"阶段：{label}\n\n章纲列表：\n{source}",
                        },
                    ],
                    temperature=0.2,
                    max_tokens=420,
                ),
                timeout=self.LLM_TEXT_TIMEOUT_SECONDS,
            )
            content = self._clean_optional_text(response["content"])
            if content:
                return content, False
        except Exception as exc:  # pragma: no cover - network/model failures
            logger.warning("Outline digest generation failed for %s: %s", label, exc)

        return self._sample_text(source, 500), True

    async def _generate_json_payload(
        self,
        messages: list[dict[str, str]],
        *,
        expect: str,
        max_tokens: int = 1800,
    ) -> Any:
        """Generate a JSON payload from the LLM, retrying once on parse failure."""
        conversation = list(messages)
        for attempt in range(2):
            response = await asyncio.wait_for(
                self.llm.generate(
                    conversation,
                    temperature=0.1,
                    max_tokens=max_tokens,
                ),
                timeout=self.LLM_JSON_TIMEOUT_SECONDS,
            )
            content = response["content"]
            try:
                parsed = self._parse_json_content(content)
            except json.JSONDecodeError:
                if attempt == 1:
                    raise
                conversation.extend(
                    [
                        {"role": "assistant", "content": content},
                        {"role": "user", "content": "请只返回合法 JSON，不要解释，不要使用 Markdown 代码块。"},
                    ]
                )
                continue

            if expect == "array" and isinstance(parsed, list):
                return parsed
            if expect == "object" and isinstance(parsed, dict):
                return parsed
            if attempt == 1:
                raise ValueError(f"Expected {expect} JSON payload")
            expected_shape = "JSON 数组" if expect == "array" else "JSON 对象"
            conversation.extend(
                [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"返回结果类型不正确。请只返回合法的 {expected_shape}，不要解释，不要使用 Markdown 代码块。"},
                ]
            )
        raise ValueError("Unable to parse JSON payload")

    def _parse_json_content(self, content: str) -> Any:
        """Parse raw LLM content into JSON."""
        stripped = self._CODE_FENCE_RE.sub("", content).strip()
        if not stripped:
            raise json.JSONDecodeError("empty", stripped, 0)

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            first_object = stripped.find("{")
            first_array = stripped.find("[")
            positions = [pos for pos in [first_object, first_array] if pos >= 0]
            if not positions:
                raise
            start = min(positions)
            end_char = "}" if stripped[start] == "{" else "]"
            end = stripped.rfind(end_char)
            if end < start:
                raise
            return json.loads(stripped[start : end + 1])

    def _normalize_detected_characters(self, payload: Any) -> list[DetectedCharacter]:
        """Validate and normalize raw character payloads."""
        if not isinstance(payload, list):
            return []
        characters: list[DetectedCharacter] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                characters.append(
                    DetectedCharacter(
                        name=str(item.get("name") or "").strip(),
                        role=self._clean_optional_text(str(item.get("role") or "")),
                        profile=item.get("profile") if isinstance(item.get("profile"), dict) else {},
                        relationships=item.get("relationships") if isinstance(item.get("relationships"), dict) else {},
                    )
                )
            except Exception:
                continue
        return [character for character in characters if character.name]

    def _normalize_detected_world_settings(self, payload: Any) -> list[DetectedWorldSetting]:
        """Validate and normalize raw world-setting payloads."""
        if not isinstance(payload, list):
            return []
        settings: list[DetectedWorldSetting] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                settings.append(
                    DetectedWorldSetting(
                        category=self._normalize_world_setting_category(str(item.get("category") or "")),
                        name=str(item.get("name") or "").strip(),
                        content=str(item.get("content") or "").strip(),
                    )
                )
            except Exception:
                continue
        return [setting for setting in settings if setting.name and setting.content]

    def _merge_characters(self, candidates: Sequence[DetectedCharacter]) -> list[DetectedCharacter]:
        """Merge duplicate character candidates by name."""
        merged: dict[str, DetectedCharacter] = {}
        counts = Counter(candidate.name for candidate in candidates if candidate.name)
        for candidate in candidates:
            if candidate.name not in merged:
                merged[candidate.name] = candidate
                continue
            existing = merged[candidate.name]
            merged[candidate.name] = DetectedCharacter(
                name=candidate.name,
                role=existing.role or candidate.role,
                profile={**candidate.profile, **existing.profile},
                relationships={**candidate.relationships, **existing.relationships},
            )
        return sorted(
            merged.values(),
            key=lambda item: (-counts[item.name], item.name),
        )

    def _merge_world_settings(self, candidates: Sequence[DetectedWorldSetting]) -> list[DetectedWorldSetting]:
        """Merge duplicate world-setting candidates by category + name."""
        merged: dict[tuple[str, str], DetectedWorldSetting] = {}
        counts = Counter((candidate.category, candidate.name) for candidate in candidates)
        for candidate in candidates:
            key = (candidate.category, candidate.name)
            if key not in merged:
                merged[key] = candidate
                continue
            existing = merged[key]
            content = existing.content
            if len(candidate.content) > len(existing.content):
                content = candidate.content
            merged[key] = DetectedWorldSetting(
                category=candidate.category,
                name=candidate.name,
                content=content,
            )
        return sorted(
            merged.values(),
            key=lambda item: (-counts[(item.category, item.name)], item.category, item.name),
        )

    def _normalize_world_setting_category(self, value: str) -> str:
        """Normalize category aliases to the supported enum."""
        normalized = value.strip().lower()
        if normalized in {
            WorldSettingCategory.MAGIC_SYSTEM,
            WorldSettingCategory.GEOGRAPHY,
            WorldSettingCategory.HISTORY,
            WorldSettingCategory.ORGANIZATION,
            WorldSettingCategory.TECHNOLOGY,
            WorldSettingCategory.CULTURE,
            WorldSettingCategory.RELIGION,
            WorldSettingCategory.ECONOMY,
            WorldSettingCategory.RULES,
            WorldSettingCategory.OTHER,
        }:
            return normalized

        alias_map = {
            "magic": WorldSettingCategory.MAGIC_SYSTEM,
            "system": WorldSettingCategory.MAGIC_SYSTEM,
            "location": WorldSettingCategory.GEOGRAPHY,
            "place": WorldSettingCategory.GEOGRAPHY,
            "faction": WorldSettingCategory.ORGANIZATION,
            "organization": WorldSettingCategory.ORGANIZATION,
            "tech": WorldSettingCategory.TECHNOLOGY,
            "tradition": WorldSettingCategory.CULTURE,
            "belief": WorldSettingCategory.RELIGION,
            "law": WorldSettingCategory.RULES,
            "rule": WorldSettingCategory.RULES,
        }
        return alias_map.get(normalized, WorldSettingCategory.OTHER)


@dataclass(slots=True)
class _OutlineResult:
    """Chapter-outline generation result."""

    content: str
    used_fallback: bool


text_import_service = TextImportService()
