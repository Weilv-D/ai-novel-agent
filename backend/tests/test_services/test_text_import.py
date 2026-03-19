"""Unit tests for the structured text import service."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.core.exceptions import BadRequestException
from app.models.text_import_job import TextImportJobStatus
from app.schemas.text_import import (
    DetectedChapter,
    DetectedCharacter,
    DetectedVolume,
    DetectedWorldSetting,
    TextImportPreview,
)
from app.services.text_import import text_import_service


class TestTextImportService:
    """Covers text splitting, chunking, and commit persistence."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("十", 10),
            ("十一", 11),
            ("十二", 12),
            ("二十", 20),
            ("二十一", 21),
            ("一百零二", 102),
        ],
    )
    def test_parse_heading_number_handles_chinese_units(self, raw: str, expected: int) -> None:
        assert text_import_service._parse_heading_number(raw) == expected

    def test_split_chapters_detects_chinese_headings(self) -> None:
        text = (
            "第一章 少年下山\n"
            "山门初开，风雪未停。\n\n"
            "第二章 夜宿客栈\n"
            "客栈里暗潮涌动。"
        )

        chapters = text_import_service._split_chapters(text)

        assert len(chapters) == 2
        assert chapters[0].chapter_number == 1
        assert chapters[0].title == "少年下山"
        assert "山门初开" in chapters[0].content
        assert chapters[1].chapter_number == 2
        assert chapters[1].title == "夜宿客栈"

    @pytest.mark.parametrize(
        ("heading", "expected_number", "expected_title"),
        [
            ("第 12 章 山门初开", 12, "山门初开"),
            ("第001章 山门初开", 1, "山门初开"),
            ("【第12章】风雪夜归", 12, "风雪夜归"),
            ("[Chapter 12] Snow Night", 12, "Snow Night"),
            ("Chapter 001 - Arrival", 1, "Arrival"),
            ("正文 第12章 山门初开", 12, "山门初开"),
        ],
    )
    def test_split_chapters_supports_extended_heading_formats(
        self,
        heading: str,
        expected_number: int,
        expected_title: str,
    ) -> None:
        text = f"{heading}\n章节内容"

        chapters = text_import_service._split_chapters(text)

        assert len(chapters) == 1
        assert chapters[0].chapter_number == expected_number
        assert chapters[0].title == expected_title

    def test_split_chapters_prioritizes_chapter_match_over_leading_volume_prefix(self) -> None:
        text = "第一卷 第十章 风起\n章节内容"

        chapters = text_import_service._split_chapters(text)

        assert len(chapters) == 1
        assert chapters[0].chapter_number == 10
        assert chapters[0].title == "风起"

    def test_detect_volumes_tracks_marked_sections(self) -> None:
        text = (
            "第一卷 山门初开\n"
            "第一章 少年下山\n"
            "章一内容\n\n"
            "第二章 夜宿客栈\n"
            "章二内容\n\n"
            "第二卷 皇城风云\n"
            "第三章 风雨欲来\n"
            "章三内容"
        )

        chapters = text_import_service._split_chapters(text)
        volumes = text_import_service._detect_volumes(text, chapters)

        assert len(volumes) == 2
        assert volumes[0].volume_number == 1
        assert volumes[0].chapter_numbers == [1, 2]
        assert volumes[1].volume_number == 2
        assert volumes[1].chapter_numbers == [3]

    def test_split_chapters_renumbers_restarted_headings(self) -> None:
        text = (
            "第一章 初入江湖\n"
            "章一内容\n\n"
            "第二章 夜探山庄\n"
            "章二内容\n\n"
            "第一部\n"
            "部一内容\n\n"
            "第二部\n"
            "部二内容\n"
        )

        chapters = text_import_service._split_chapters(text)

        assert [chapter.chapter_number for chapter in chapters] == [1, 2, 3, 4]
        assert [chapter.title for chapter in chapters] == ["初入江湖", "夜探山庄", "第一部", "第二部"]
        assert "部一内容" in chapters[2].content
        assert "部二内容" in chapters[3].content

    def test_split_chapters_deduplicates_adjacent_duplicate_blocks(self) -> None:
        text = (
            "第十四章\n"
            "甲内容\n\n"
            "第十四章\n"
            "甲内容\n\n"
            "第十五章\n"
            "乙内容\n"
        )

        chapters = text_import_service._split_chapters(text)

        assert len(chapters) == 2
        assert [chapter.title for chapter in chapters] == ["第十四章", "第十五章"]
        assert [chapter.content for chapter in chapters] == ["甲内容", "乙内容"]

    def test_chunk_text_creates_overlap(self) -> None:
        text = "0123456789" * 40
        chunks = text_import_service._chunk_text(text, max_chars=80, overlap=10)

        assert len(chunks) > 1
        assert chunks[0][-10:] == chunks[1][:10]

    def test_normalize_detected_structure_splits_oversized_chapters(self) -> None:
        oversized_content = "甲" * (text_import_service.MAX_STORED_CHAPTER_CHARS + 20)
        preview = TextImportPreview(project_name="超长章节项目")

        chapters, volumes = text_import_service._normalize_detected_structure(
            chapters=[
                DetectedChapter(
                    chapter_number=1,
                    title="超长章节",
                    content=oversized_content,
                    outline=None,
                )
            ],
            volumes=[
                DetectedVolume(
                    volume_number=1,
                    title="第一卷",
                    outline=None,
                    chapter_numbers=[1],
                )
            ],
            preview=preview,
        )

        assert len(chapters) == 2
        assert chapters[0].chapter_number == 1
        assert chapters[1].chapter_number == 2
        assert chapters[0].title == "超长章节（1/2）"
        assert chapters[1].title == "超长章节（2/2）"
        assert volumes[0].chapter_numbers == [1, 2]
        assert any("超长章节已自动拆分" in warning for warning in preview.warnings)

    def test_should_enqueue_background_job_for_large_import(self) -> None:
        chapters = [
            DetectedChapter(
                chapter_number=index,
                title=f"第{index}章",
                content="正文" * 20,
                outline=None,
            )
            for index in range(1, 201)
        ]

        assert text_import_service.should_enqueue_background_job(chapters) is True

    @pytest.mark.asyncio
    async def test_build_client_preview_compacts_large_payload(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        preview = TextImportPreview(
            project_name="大体量预览",
            chapters=[
                DetectedChapter(
                    chapter_number=1,
                    title="第一章",
                    content="正文" * 5000,
                    outline="章纲",
                )
            ],
        )

        async def fake_store(_preview: TextImportPreview) -> str:
            return "preview-token"

        monkeypatch.setattr(text_import_service, "_store_preview_snapshot", fake_store)
        monkeypatch.setattr(text_import_service, "MAX_INLINE_PREVIEW_CHARS", 100)

        client_preview = await text_import_service._build_client_preview(preview)

        assert client_preview.preview_id == "preview-token"
        assert client_preview.compact_preview is True
        assert client_preview.chapters[0].content_truncated is True
        assert client_preview.chapters[0].content_length == len(preview.chapters[0].content)

    @pytest.mark.asyncio
    async def test_analyze_reports_normalized_chapter_count_in_structure_detection(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        oversized_content = "甲" * (text_import_service.MAX_STORED_CHAPTER_CHARS + 20)
        text = f"第一章\n{oversized_content}"

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)

        async def fake_generate_chapter_outline(
            _chapter: DetectedChapter,
            *,
            use_excerpt_only: bool = False,
        ) -> SimpleNamespace:
            del use_excerpt_only
            return SimpleNamespace(content="章纲", used_fallback=False)

        async def fake_generate_project_summary(
            _chapters: list[DetectedChapter],
            *,
            project_name: str,
            genre: str | None,
        ) -> dict[str, str | bool | None]:
            return {
                "summary": "摘要",
                "story_outline": "总纲",
                "genre": genre,
                "used_fallback": False,
            }

        async def fake_generate_volume_outlines(
            volumes: list[DetectedVolume],
            _chapters: list[DetectedChapter],
        ) -> list[str | None]:
            return [volume.outline for volume in volumes]

        async def fake_extract_characters(
            _chapters: list[DetectedChapter],
            *,
            group_limit: int | None = None,
            refine_limit: int | None = None,
        ) -> list[DetectedCharacter]:
            del group_limit, refine_limit
            return []

        async def fake_extract_world_settings(
            _chapters: list[DetectedChapter],
            *,
            group_limit: int | None = None,
            refine_limit: int | None = None,
        ) -> list[DetectedWorldSetting]:
            del group_limit, refine_limit
            return []

        async def fake_build_client_preview(preview: TextImportPreview) -> TextImportPreview:
            return preview

        monkeypatch.setattr(text_import_service, "_generate_chapter_outline", fake_generate_chapter_outline)
        monkeypatch.setattr(text_import_service, "_generate_project_summary", fake_generate_project_summary)
        monkeypatch.setattr(text_import_service, "_generate_volume_outlines", fake_generate_volume_outlines)
        monkeypatch.setattr(text_import_service, "_extract_characters", fake_extract_characters)
        monkeypatch.setattr(text_import_service, "_extract_world_settings", fake_extract_world_settings)
        monkeypatch.setattr(text_import_service, "_build_client_preview", fake_build_client_preview)

        events = [event async for event in text_import_service.analyze(text, "超长章节项目")]

        structure_event = next(
            event
            for event in events
            if event.phase == "structure_detection" and event.progress > 0.1
        )

        assert structure_event.message == "已识别 1 个卷 / 2 个章节"
        assert structure_event.data["chapters"] == 2
        assert any("超长章节已自动拆分" in warning for warning in structure_event.data["warnings"])

    @pytest.mark.asyncio
    async def test_analyze_large_import_generates_full_outline_progress(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapters_text = "\n\n".join(
            f"第{index}章 标题{index}\n章节内容{index}"
            for index in range(1, text_import_service.BACKGROUND_IMPORT_CHAPTER_THRESHOLD + 3)
        )

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)

        async def fake_generate_chapter_outline(
            chapter: DetectedChapter,
            *,
            use_excerpt_only: bool = False,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                content=f"{chapter.title}-{'节选' if use_excerpt_only else '完整'}章纲",
                used_fallback=False,
            )

        async def fake_generate_project_summary(
            _chapters: list[DetectedChapter],
            *,
            project_name: str,
            genre: str | None,
        ) -> dict[str, str | bool | None]:
            return {
                "summary": "摘要",
                "story_outline": "总纲",
                "genre": genre,
                "used_fallback": False,
            }

        async def fake_generate_volume_outlines(
            volumes: list[DetectedVolume],
            _chapters: list[DetectedChapter],
        ) -> list[str | None]:
            return [volume.outline for volume in volumes]

        async def fake_extract_characters(
            _chapters: list[DetectedChapter],
            *,
            group_limit: int | None = None,
            refine_limit: int | None = None,
        ) -> list[DetectedCharacter]:
            assert group_limit is None
            assert refine_limit is None
            return []

        async def fake_extract_world_settings(
            _chapters: list[DetectedChapter],
            *,
            group_limit: int | None = None,
            refine_limit: int | None = None,
        ) -> list[DetectedWorldSetting]:
            assert group_limit is None
            assert refine_limit is None
            return []

        async def fake_build_client_preview(preview: TextImportPreview) -> TextImportPreview:
            return preview

        monkeypatch.setattr(text_import_service, "_generate_chapter_outline", fake_generate_chapter_outline)
        monkeypatch.setattr(text_import_service, "_generate_project_summary", fake_generate_project_summary)
        monkeypatch.setattr(text_import_service, "_generate_volume_outlines", fake_generate_volume_outlines)
        monkeypatch.setattr(text_import_service, "_extract_characters", fake_extract_characters)
        monkeypatch.setattr(text_import_service, "_extract_world_settings", fake_extract_world_settings)
        monkeypatch.setattr(text_import_service, "_build_client_preview", fake_build_client_preview)

        events = [event async for event in text_import_service.analyze(chapters_text, "大文件项目")]

        outline_event = next(
            event
            for event in events
            if event.phase == "outline_extraction" and "已生成" in event.message
        )
        completed_preview = events[-1].data["preview"]

        assert outline_event.message == f"已生成 1/{text_import_service.BACKGROUND_IMPORT_CHAPTER_THRESHOLD + 2} 个章纲"
        assert all("采样" not in warning for warning in completed_preview["warnings"])
        assert all(chapter["outline"] for chapter in completed_preview["chapters"])

    @pytest.mark.asyncio
    async def test_process_background_job_completes_with_full_preview(
        self,
        db_session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)

        async def fake_generate_chapter_outline(
            chapter: DetectedChapter,
            *,
            use_excerpt_only: bool = False,
        ) -> SimpleNamespace:
            del use_excerpt_only
            return SimpleNamespace(content=f"{chapter.title}章纲", used_fallback=False)

        async def fake_generate_project_summary(
            _chapters: list[DetectedChapter],
            *,
            project_name: str,
            genre: str | None,
        ) -> dict[str, str | bool | None]:
            return {
                "summary": f"{project_name}摘要",
                "story_outline": "完整总纲",
                "genre": genre or "仙侠",
                "used_fallback": False,
            }

        async def fake_generate_volume_outlines(
            volumes: list[DetectedVolume],
            _chapters: list[DetectedChapter],
        ) -> list[str | None]:
            return [f"{volume.title or '卷'}卷纲" for volume in volumes]

        async def fake_extract_characters(
            chapters: list[DetectedChapter],
            **kwargs,
        ) -> list[DetectedCharacter]:
            del chapters, kwargs
            return []

        async def fake_extract_world_settings(
            chapters: list[DetectedChapter],
            **kwargs,
        ) -> list[DetectedWorldSetting]:
            del chapters, kwargs
            return []

        async def fake_build_client_preview(preview: TextImportPreview) -> TextImportPreview:
            return preview

        monkeypatch.setattr(text_import_service, "_generate_chapter_outline", fake_generate_chapter_outline)
        monkeypatch.setattr(text_import_service, "_generate_project_summary", fake_generate_project_summary)
        monkeypatch.setattr(text_import_service, "_generate_volume_outlines", fake_generate_volume_outlines)
        monkeypatch.setattr(text_import_service, "_extract_characters", fake_extract_characters)
        monkeypatch.setattr(text_import_service, "_extract_world_settings", fake_extract_world_settings)
        monkeypatch.setattr(text_import_service, "_build_client_preview", fake_build_client_preview)

        job = await text_import_service.create_background_job(
            db_session,
            text="第一章 起\n正文甲\n\n第二章 承\n正文乙",
            project_name="后台任务项目",
            genre="仙侠",
            source_filename="novel.txt",
            source_encoding="utf-8",
        )
        await db_session.commit()

        await text_import_service.process_background_job(db_session, job.id)

        stored_job = await text_import_service.get_background_job(db_session, job.id)
        response = text_import_service.build_background_job_response(stored_job)

        assert stored_job.status == TextImportJobStatus.COMPLETED.value
        assert stored_job.phase == "completed"
        assert response.preview is not None
        assert len(response.preview.chapters) == 2
        assert response.preview.chapters[0].outline == "起章纲"
        assert response.preview.summary == "后台任务项目摘要"

    @pytest.mark.asyncio
    async def test_process_background_job_marks_failure(
        self,
        db_session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)

        async def failing_generate_chapter_outline(
            chapter: DetectedChapter,
            *,
            use_excerpt_only: bool = False,
        ) -> SimpleNamespace:
            del chapter, use_excerpt_only
            raise RuntimeError("boom")

        monkeypatch.setattr(text_import_service, "_generate_chapter_outline", failing_generate_chapter_outline)

        job = await text_import_service.create_background_job(
            db_session,
            text="第一章 起\n正文甲",
            project_name="失败任务项目",
            genre="仙侠",
        )
        await db_session.commit()

        await text_import_service.process_background_job(db_session, job.id)

        stored_job = await text_import_service.get_background_job(db_session, job.id)

        assert stored_job.status == TextImportJobStatus.FAILED.value
        assert stored_job.phase == "error"
        assert stored_job.error_detail == "boom"

    def test_merge_confirmed_preview_preserves_full_content_from_compact_preview(self) -> None:
        stored_preview = TextImportPreview(
            preview_id="preview-token",
            project_name="原始项目",
            chapters=[
                DetectedChapter(
                    chapter_number=1,
                    title="第一章",
                    content="完整正文" * 100,
                    outline="原始章纲",
                )
            ],
        )
        edited_preview = TextImportPreview(
            preview_id="preview-token",
            compact_preview=True,
            project_name="原始项目",
            chapters=[
                DetectedChapter(
                    chapter_number=1,
                    title="第一章（已编辑）",
                    content="节选正文",
                    outline="编辑后章纲",
                    content_truncated=True,
                )
            ],
        )

        merged_preview = text_import_service._merge_confirmed_preview(stored_preview, edited_preview)

        assert merged_preview.chapters[0].title == "第一章（已编辑）"
        assert merged_preview.chapters[0].outline == "编辑后章纲"
        assert merged_preview.chapters[0].content == stored_preview.chapters[0].content

    def test_novel_fixture_regression_recovers_18_chapters(self) -> None:
        fixture_path = Path(__file__).resolve().parents[3] / "others" / "九州·飘零书·商博良.txt"
        raw_text = fixture_path.read_text(encoding="utf-8")
        text = text_import_service._normalize_text(raw_text)
        preview = TextImportPreview(project_name="九州·飘零书·商博良")

        chapters = text_import_service._split_chapters(text)
        volumes = text_import_service._detect_volumes(text, chapters)
        normalized_chapters, normalized_volumes = text_import_service._normalize_detected_structure(
            chapters=chapters,
            volumes=volumes,
            preview=preview,
        )

        assert len(normalized_chapters) == 18
        assert [chapter.chapter_number for chapter in normalized_chapters] == list(range(1, 19))
        assert normalized_chapters[10].title == "第十一章"
        assert normalized_chapters[-1].title == "第十八章"
        assert len(normalized_volumes) == 1
        assert normalized_volumes[0].title == "第一卷"
        assert normalized_volumes[0].chapter_numbers == list(range(1, 19))

    @pytest.mark.asyncio
    async def test_generate_chapter_outline_excerpt_mode_skips_chunk_summarization(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapter = DetectedChapter(
            chapter_number=1,
            title="第一章",
            content="甲" * (text_import_service.CHAPTER_OUTLINE_MAX_CHARS + 500),
            outline=None,
        )
        called = False

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)

        async def fake_summarize_chunk(_chunk: str) -> str:
            nonlocal called
            called = True
            return "分块摘要"

        async def fake_generate(*args, **kwargs):
            del args, kwargs
            response = SimpleNamespace()
            response.__getitem__ = None
            return {"content": "章纲内容"}

        monkeypatch.setattr(text_import_service, "_summarize_chunk", fake_summarize_chunk)
        monkeypatch.setattr(text_import_service.llm, "generate", fake_generate)

        result = await text_import_service._generate_chapter_outline(chapter, use_excerpt_only=True)

        assert result.content == "章纲内容"
        assert called is False

    @pytest.mark.asyncio
    async def test_generate_volume_outlines_uses_all_volume_chapters(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        volumes = [
            DetectedVolume(volume_number=1, title="第一卷", outline=None, chapter_numbers=[1, 2, 3]),
        ]
        chapters = [
            DetectedChapter(chapter_number=index, title=f"第{index}章", content="正文", outline=f"章纲{index}")
            for index in range(1, 4)
        ]
        captured: list[list[int]] = []

        async def fake_prepare_outline_digest(
            scoped: list[DetectedChapter],
            *,
            label: str,
        ) -> tuple[str, bool]:
            del label
            captured.append([chapter.chapter_number for chapter in scoped])
            return "章纲摘要", False

        monkeypatch.setattr(text_import_service, "_prepare_outline_digest", fake_prepare_outline_digest)
        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: False)

        outlines = await text_import_service._generate_volume_outlines(
            volumes,
            chapters,
        )

        assert captured == [[1, 2, 3]]
        assert len(outlines) == 1

    @pytest.mark.asyncio
    async def test_extract_characters_keeps_partial_results_when_subgroups_fail(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapters = [
            DetectedChapter(
                chapter_number=index,
                title=f"第{index}章",
                content="章节原文",
                outline="章节章纲",
            )
            for index in range(1, 7)
        ]

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)
        monkeypatch.setattr(text_import_service, "ENTITY_GROUP_SIZE", 3)
        monkeypatch.setattr(text_import_service, "ENTITY_EXTRACTION_BATCH_SIZE", 2)

        async def fake_extract_character_group(group):
            if group[0].chapter_number == 4:
                raise TimeoutError()
            return [
                DetectedCharacter(
                    name=f"角色{group[0].chapter_number}",
                    role="主角",
                    profile={},
                    relationships={},
                )
            ]

        monkeypatch.setattr(text_import_service, "_extract_character_group", fake_extract_character_group)

        characters = await text_import_service._extract_characters(chapters)

        assert [character.name for character in characters] == ["角色1"]

    @pytest.mark.asyncio
    async def test_extract_world_settings_keeps_partial_results_when_subgroups_fail(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapters = [
            DetectedChapter(
                chapter_number=index,
                title=f"第{index}章",
                content="章节原文",
                outline="章节章纲",
            )
            for index in range(1, 7)
        ]

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)
        monkeypatch.setattr(text_import_service, "ENTITY_GROUP_SIZE", 3)
        monkeypatch.setattr(text_import_service, "ENTITY_EXTRACTION_BATCH_SIZE", 2)

        async def fake_extract_world_setting_group(group, categories):
            del categories
            if group[0].chapter_number == 4:
                raise TimeoutError()
            return [
                DetectedWorldSetting(
                    category="technology",
                    name=f"设定{group[0].chapter_number}",
                    content="设定内容",
                )
            ]

        monkeypatch.setattr(text_import_service, "_extract_world_setting_group", fake_extract_world_setting_group)

        settings = await text_import_service._extract_world_settings(chapters)

        assert "设定1" in [setting.name for setting in settings]

    @pytest.mark.asyncio
    async def test_extract_characters_retries_with_outline_only_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapters = [
            DetectedChapter(
                chapter_number=index,
                title=f"第{index}章",
                content="章节原文",
                outline="角色甲与角色乙在城中碰面。",
            )
            for index in range(1, 3)
        ]

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)

        async def fake_extract_character_group(
            group,
            *,
            include_text_sample=True,
            max_characters=8,
            sample_chars=None,
            max_tokens=1200,
        ):
            del group, max_characters, sample_chars, max_tokens
            if include_text_sample:
                raise TimeoutError()
            return [
                DetectedCharacter(
                    name="角色甲",
                    role="主角",
                    profile={},
                    relationships={},
                ),
                DetectedCharacter(
                    name="角色乙",
                    role="配角",
                    profile={},
                    relationships={},
                ),
            ]

        monkeypatch.setattr(text_import_service, "_extract_character_group", fake_extract_character_group)

        characters = await text_import_service._extract_characters(chapters)

        characters_by_name = {character.name: character for character in characters}
        assert set(characters_by_name) == {"角色甲", "角色乙"}
        assert characters_by_name["角色甲"].relationships["角色乙"] == "同章出现"
        assert characters_by_name["角色乙"].relationships["角色甲"] == "同章出现"

    @pytest.mark.asyncio
    async def test_extract_characters_requires_llm(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapters = [
            DetectedChapter(
                chapter_number=1,
                title="初入青州城",
                content=(
                    "林霄低声说道，他要先进青州城。"
                    "苏晚点头答应，跟着林霄一起走进城门。"
                    "林霄看着苏晚，提醒她小心天机阁的人。"
                ),
                outline="林霄与苏晚在青州城碰头，准备调查天机阁。",
            ),
            DetectedChapter(
                chapter_number=2,
                title="夜探天机阁",
                content=(
                    "林霄抱拳说道，今夜要潜入天机阁。"
                    "苏晚低声问他是否已经摸清路线。"
                    "林霄点头，让苏晚先守在后巷。"
                ),
                outline="林霄和苏晚配合夜探天机阁。",
            ),
        ]

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: False)

        with pytest.raises(BadRequestException, match="未配置 LLM"):
            await text_import_service._extract_characters(chapters)

    @pytest.mark.asyncio
    async def test_extract_world_settings_requires_llm(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapters = [
            DetectedChapter(
                chapter_number=1,
                title="青州城风声",
                content=(
                    "青州城里人人都在议论灵脉体系失衡。"
                    "天机阁派出弟子巡视青州城的城门。"
                    "灵脉体系若继续紊乱，整座青州城都会受影响。"
                ),
                outline="青州城与天机阁都围绕灵脉体系出现异动。",
            ),
            DetectedChapter(
                chapter_number=2,
                title="阁中议事",
                content=(
                    "天机阁长老认为灵脉体系必须重新梳理。"
                    "青州城的商路和守备都要听命于天机阁。"
                ),
                outline="天机阁召开议事，讨论青州城的灵脉体系。",
            ),
        ]

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: False)

        with pytest.raises(BadRequestException, match="未配置 LLM"):
            await text_import_service._extract_world_settings(chapters)

    @pytest.mark.asyncio
    async def test_extract_characters_refines_cards_with_llm(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapters = [
            DetectedChapter(
                chapter_number=1,
                title="第一章",
                content="林霄与苏晚同行。",
                outline="林霄与苏晚同行。",
            )
        ]

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)

        async def fake_extract_character_group(group):
            del group
            return [
                DetectedCharacter(
                    name="林霄",
                    role="主角",
                    profile={},
                    relationships={},
                )
            ]

        async def fake_refine_character_cards(candidates, source_chapters, *, limit=None):
            del source_chapters, limit
            return [
                candidates[0].model_copy(
                    update={
                        "profile": {"background": "完整背景", "personality": "冷静果断"},
                        "relationships": {"苏晚": "同行者"},
                    }
                )
            ]

        monkeypatch.setattr(text_import_service, "_extract_character_group", fake_extract_character_group)
        monkeypatch.setattr(text_import_service, "_refine_character_cards", fake_refine_character_cards)
        monkeypatch.setattr(text_import_service, "_extract_characters_heuristic", lambda chapters: [])

        characters = await text_import_service._extract_characters(chapters)

        assert characters[0].profile["background"] == "完整背景"
        assert characters[0].relationships["苏晚"] == "同行者"

    @pytest.mark.asyncio
    async def test_extract_world_settings_refines_cards_with_llm(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        chapters = [
            DetectedChapter(
                chapter_number=1,
                title="第一章",
                content="灵脉体系开始失衡。",
                outline="灵脉体系开始失衡。",
            )
        ]

        monkeypatch.setattr(text_import_service, "_llm_ready", lambda: True)

        async def fake_extract_world_setting_group(group, categories):
            del group, categories
            return [
                DetectedWorldSetting(
                    category="other",
                    name="灵脉体系",
                    content="标题级描述",
                )
            ]

        async def fake_refine_world_settings(candidates, source_chapters, *, limit=None):
            del source_chapters, limit
            return [
                candidates[0].model_copy(
                    update={
                        "category": "magic_system",
                        "content": "灵脉体系控制修行与冲突升级，是全书核心力量规则。",
                    }
                )
            ]

        monkeypatch.setattr(text_import_service, "_extract_world_setting_group", fake_extract_world_setting_group)
        monkeypatch.setattr(text_import_service, "_refine_world_settings", fake_refine_world_settings)
        monkeypatch.setattr(text_import_service, "_extract_world_settings_heuristic", lambda chapters: [])

        settings = await text_import_service._extract_world_settings(chapters)

        assert settings[0].category == "magic_system"
        assert "核心力量规则" in settings[0].content

    @pytest.mark.asyncio
    async def test_commit_creates_project_graph(self, db_session) -> None:
        preview = TextImportPreview(
            project_name="导入测试项目",
            genre="玄幻",
            summary="项目摘要",
            story_outline="项目总纲",
            volumes=[
                DetectedVolume(
                    volume_number=1,
                    title="第一卷 山门初开",
                    outline="卷纲一",
                    chapter_numbers=[1, 2],
                )
            ],
            chapters=[
                DetectedChapter(
                    chapter_number=1,
                    title="少年下山",
                    content="第一章原文",
                    outline="第一章章纲",
                ),
                DetectedChapter(
                    chapter_number=2,
                    title="夜宿客栈",
                    content="第二章原文",
                    outline="第二章章纲",
                ),
            ],
            characters=[
                DetectedCharacter(
                    name="林霄",
                    role="主角",
                    profile={"personality": "冷静"},
                    relationships={"苏晚": "同行者"},
                )
            ],
            world_settings=[
                DetectedWorldSetting(
                    category="magic_system",
                    name="灵气体系",
                    content="天地间存在灵气，修士以吐纳炼化。",
                )
            ],
        )

        response = await text_import_service.commit(db_session, preview)

        assert response.project_name == "导入测试项目"
        assert response.imported_counts == {
            "projects": 1,
            "volumes": 1,
            "chapters": 2,
            "characters": 1,
            "world_settings": 1,
            "memories": 2,
            "dependencies": 6,
        }

        project_id = str(response.project_id)
        volumes = (
            await db_session.execute(
                text(
                    """
                    select volume_number, title
                    from volumes
                    where project_id = :project_id
                    order by volume_number asc
                    """
                ),
                {"project_id": project_id},
            )
        )
        chapters = (
            await db_session.execute(
                text(
                    """
                    select chapter_number, title, content, outline
                    from chapters
                    where project_id = :project_id
                    order by chapter_number asc
                    """
                ),
                {"project_id": project_id},
            )
        )
        characters = (
            await db_session.execute(
                text(
                    """
                    select name
                    from characters
                    where project_id = :project_id
                    order by name asc
                    """
                ),
                {"project_id": project_id},
            )
        )
        settings = (
            await db_session.execute(
                text(
                    """
                    select name
                    from world_settings
                    where project_id = :project_id
                    order by name asc
                    """
                ),
                {"project_id": project_id},
            )
        )
        memories = (
            await db_session.execute(
                text(
                    """
                    select memory_type, content, metadata
                    from memories
                    where project_id = :project_id
                    order by created_at asc
                    """
                ),
                {"project_id": project_id},
            )
        )
        dependencies = (
            await db_session.execute(
                text(
                    """
                    select dependency_type
                    from dependencies
                    where project_id = :project_id
                    order by created_at asc
                    """
                ),
                {"project_id": project_id},
            )
        )
        volume_rows = volumes.mappings().all()
        chapter_rows = chapters.mappings().all()
        character_rows = characters.mappings().all()
        setting_rows = settings.mappings().all()
        memory_rows = memories.mappings().all()
        dependency_rows = dependencies.mappings().all()

        assert len(volume_rows) == 1
        assert volume_rows[0]["title"] == "第一卷 山门初开"
        assert len(chapter_rows) == 2
        assert chapter_rows[0]["content"] == "第一章原文"
        assert chapter_rows[1]["outline"] == "第二章章纲"
        assert len(character_rows) == 1
        assert character_rows[0]["name"] == "林霄"
        assert len(setting_rows) == 1
        assert setting_rows[0]["name"] == "灵气体系"
        assert len(memory_rows) == 2
        assert all(memory["memory_type"] == "episode" for memory in memory_rows)
        assert any('"chapter_number": 1' in (memory["metadata"] or "") for memory in memory_rows)
        assert len(dependency_rows) == 6
        assert any(dependency["dependency_type"] == "precedes" for dependency in dependency_rows)

    @pytest.mark.asyncio
    async def test_commit_uses_stored_snapshot_for_compact_preview(
        self,
        db_session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        stored_preview = TextImportPreview(
            preview_id="preview-token",
            project_name="长文本导入项目",
            summary="原始摘要",
            chapters=[
                DetectedChapter(
                    chapter_number=1,
                    title="第一章",
                    content="完整正文" * 1000,
                    outline="原始章纲",
                )
            ],
        )
        edited_preview = TextImportPreview(
            preview_id="preview-token",
            compact_preview=True,
            project_name="长文本导入项目（已确认）",
            chapters=[
                DetectedChapter(
                    chapter_number=1,
                    title="第一章（已编辑）",
                    content="节选正文",
                    outline="编辑后章纲",
                    content_truncated=True,
                )
            ],
        )

        async def fake_load_preview_snapshot(preview_id: str) -> TextImportPreview | None:
            assert preview_id == "preview-token"
            return stored_preview

        deleted_preview_ids: list[str | None] = []

        async def fake_delete_preview_snapshot(preview_id: str | None) -> None:
            deleted_preview_ids.append(preview_id)

        monkeypatch.setattr(text_import_service, "_load_preview_snapshot", fake_load_preview_snapshot)
        monkeypatch.setattr(text_import_service, "_delete_preview_snapshot", fake_delete_preview_snapshot)

        response = await text_import_service.commit(db_session, edited_preview)

        chapters = (
            await db_session.execute(
                text(
                    """
                    select title, outline, content
                    from chapters
                    where project_id = :project_id
                    order by chapter_number asc
                    """
                ),
                {"project_id": str(response.project_id)},
            )
        )
        chapter_rows = chapters.mappings().all()

        assert response.project_name == "长文本导入项目（已确认）"
        assert len(chapter_rows) == 1
        assert chapter_rows[0]["title"] == "第一章（已编辑）"
        assert chapter_rows[0]["outline"] == "编辑后章纲"
        assert chapter_rows[0]["content"] == stored_preview.chapters[0].content
        assert deleted_preview_ids == ["preview-token"]
