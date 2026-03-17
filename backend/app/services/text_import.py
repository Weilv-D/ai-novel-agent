"""Structured text import service."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.schemas.chapter import ChapterCreate, ChapterStatus, VolumeCreate
from app.schemas.character import CharacterCreate
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
from app.schemas.world_setting import WorldSettingCategory, WorldSettingCreate
from app.services.chapter import chapter_service, volume_service
from app.services.character import character_service
from app.services.llm import llm_service
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

    MAX_FILE_SIZE = 15 * 1024 * 1024
    MIN_CHAR_COUNT = 500
    CHAPTER_OUTLINE_MAX_CHARS = 12000
    CHAPTER_OUTLINE_BATCH_SIZE = 4
    ENTITY_GROUP_SIZE = 5
    ENTITY_SAMPLE_LIMIT = 60000
    LLM_TEXT_TIMEOUT_SECONDS = 20
    LLM_JSON_TIMEOUT_SECONDS = 25

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
        preview.chapters = chapters
        preview.volumes = self._detect_volumes(normalized_text, chapters)
        if len(chapters) == 1:
            self._append_warning(preview, "未检测到稳定章节标记，已按单章导入。")

        yield TextImportProgress(
            phase="structure_detection",
            progress=0.15,
            message=f"已识别 {len(preview.volumes)} 个卷 / {len(chapters)} 个章节",
            data={
                "volumes": len(preview.volumes),
                "chapters": len(chapters),
                "warnings": list(preview.warnings),
            },
        )

        outline_warnings = 0
        total_chapters = max(len(chapters), 1)
        for start in range(0, len(chapters), self.CHAPTER_OUTLINE_BATCH_SIZE):
            batch = chapters[start : start + self.CHAPTER_OUTLINE_BATCH_SIZE]
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
                message=f"已生成 {completed}/{len(chapters)} 个章纲",
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

        yield TextImportProgress(
            phase="completed",
            progress=1.0,
            message="分析完成，请预览后确认导入",
            data={"preview": preview.model_dump(mode="json")},
        )

    async def commit(
        self,
        db: AsyncSession,
        preview: TextImportPreview,
    ) -> TextImportResponse:
        """Create project data from a confirmed text-import preview."""
        project = await project_service.create_project(
            db,
            obj_in=ProjectCreate(
                name=preview.project_name,
                genre=self._clean_optional_text(preview.genre),
                summary=self._clean_optional_text(preview.summary),
                story_outline=self._clean_optional_text(preview.story_outline),
            ),
        )

        imported_counts: dict[str, int] = {"projects": 1}
        chapter_to_volume_id: dict[int, Any] = {}
        volume_records = preview.volumes or self._build_default_volumes(preview.chapters)

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
            for chapter_number in volume.chapter_numbers:
                chapter_to_volume_id[chapter_number] = created_volume.id
            imported_counts["volumes"] = imported_counts.get("volumes", 0) + 1

        for index, chapter in enumerate(preview.chapters, start=1):
            chapter_number = chapter.chapter_number or index
            await chapter_service.create_with_project(
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
            imported_counts["chapters"] = imported_counts.get("chapters", 0) + 1

        for character in preview.characters:
            await character_service.create_with_project(
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
            imported_counts["characters"] = imported_counts.get("characters", 0) + 1

        for world_setting in preview.world_settings:
            await world_setting_service.create_with_project(
                db,
                obj_in=WorldSettingCreate(
                    project_id=project.id,
                    category=world_setting.category,
                    name=world_setting.name,
                    content=world_setting.content,
                ),
                project_id=project.id,
            )
            imported_counts["world_settings"] = imported_counts.get("world_settings", 0) + 1

        await db.commit()

        return TextImportResponse(
            project_id=project.id,
            project_name=project.name,
            imported_counts=imported_counts,
        )

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

        outline_block = self._build_outline_block(chapters)
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
                                f"章纲列表：\n{outline_block}"
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
                        "used_fallback": False,
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

        groups = [chapters[index : index + self.ENTITY_GROUP_SIZE] for index in range(0, len(chapters), self.ENTITY_GROUP_SIZE)]
        candidates: list[DetectedCharacter] = []
        for group in groups:
            payload = await self._generate_json_payload(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是中文小说人物策划编辑。请从提供的章纲和原文采样中提取关键角色，"
                            "只返回 JSON 数组。每个元素字段为 name、role、profile、relationships。"
                            "profile 和 relationships 必须是 JSON 对象。不要返回超过 8 个角色。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"章纲：\n{self._build_outline_block(group)}\n\n"
                            f"原文采样：\n{self._build_text_sample(group, max_chars=15000)}"
                        ),
                    },
                ],
                expect="array",
            )
            candidates.extend(self._normalize_detected_characters(payload))

        return self._merge_characters(candidates)[:20]

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
        groups = [chapters[index : index + self.ENTITY_GROUP_SIZE] for index in range(0, len(chapters), self.ENTITY_GROUP_SIZE)]
        candidates: list[DetectedWorldSetting] = []
        for group in groups:
            payload = await self._generate_json_payload(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是中文小说世界观策划编辑。请从提供的章纲和原文采样中提取关键设定，"
                            "只返回 JSON 数组。每个元素字段为 category、name、content。"
                            f"category 必须从以下枚举中选择：{categories}。不要返回超过 6 个设定。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"章纲：\n{self._build_outline_block(group)}\n\n"
                            f"原文采样：\n{self._build_text_sample(group, max_chars=15000)}"
                        ),
                    },
                ],
                expect="array",
            )
            candidates.extend(self._normalize_detected_world_settings(payload))

        return self._merge_world_settings(candidates)[:15]

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
                                    f"卷内章纲：\n{self._build_outline_block(scoped)}"
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

        for line_index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            volume_match = self._match_volume_heading(stripped, has_markdown_chapters)
            if volume_match is not None:
                volume_number = volume_match["number"] or next_volume_number
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
                chapter_number = chapter_match["number"] or next_chapter_number
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
            return {
                "number": number,
                "title": self._clean_optional_text(chapter_match.group("title")),
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
            return {
                "number": number,
                "title": self._clean_optional_text(volume_match.group("title")),
            }

        if allow_markdown:
            markdown_match = self._MARKDOWN_VOLUME_RE.match(line)
            if markdown_match:
                title = self._clean_optional_text(markdown_match.group("title"))
                if title:
                    return {"number": None, "title": title}
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

    def _build_outline_block(self, chapters: Sequence[DetectedChapter]) -> str:
        """Render chapter outlines for prompting."""
        return "\n".join(
            [
                f"第{chapter.chapter_number}章 {chapter.title or '未命名'}：{chapter.outline or self._fallback_chapter_outline(chapter)}"
                for chapter in chapters
            ]
        )

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

    async def _generate_json_payload(
        self,
        messages: list[dict[str, str]],
        *,
        expect: str,
    ) -> Any:
        """Generate a JSON payload from the LLM, retrying once on parse failure."""
        conversation = list(messages)
        for attempt in range(2):
            response = await asyncio.wait_for(
                self.llm.generate(
                    conversation,
                    temperature=0.1,
                    max_tokens=1800,
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
            raise ValueError(f"Expected {expect} JSON payload")
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
