"""Unit tests for the structured text import service."""

from __future__ import annotations

import pytest

from app.schemas.text_import import (
    DetectedChapter,
    DetectedCharacter,
    DetectedVolume,
    DetectedWorldSetting,
    TextImportPreview,
)
from app.services.chapter import chapter_service, volume_service
from app.services.character import character_service
from app.services.text_import import text_import_service
from app.services.world_setting import world_setting_service


class TestTextImportService:
    """Covers text splitting, chunking, and commit persistence."""

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

        assert [setting.name for setting in settings] == ["设定1"]

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
        }

        volumes = await volume_service.get_by_project(db_session, project_id=response.project_id)
        chapters = await chapter_service.get_by_project(db_session, project_id=response.project_id)
        characters = await character_service.get_by_project(db_session, project_id=response.project_id)
        settings = await world_setting_service.get_by_project(db_session, project_id=response.project_id)

        assert len(volumes) == 1
        assert volumes[0].title == "第一卷 山门初开"
        assert len(chapters) == 2
        assert chapters[0].content == "第一章原文"
        assert chapters[1].outline == "第二章章纲"
        assert len(characters) == 1
        assert characters[0].name == "林霄"
        assert len(settings) == 1
        assert settings[0].name == "灵气体系"

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

        chapters = await chapter_service.get_by_project(db_session, project_id=response.project_id)

        assert response.project_name == "长文本导入项目（已确认）"
        assert len(chapters) == 1
        assert chapters[0].title == "第一章（已编辑）"
        assert chapters[0].outline == "编辑后章纲"
        assert chapters[0].content == stored_preview.chapters[0].content
        assert deleted_preview_ids == ["preview-token"]
