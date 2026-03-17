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

    def test_chunk_text_creates_overlap(self) -> None:
        text = "0123456789" * 40
        chunks = text_import_service._chunk_text(text, max_chars=80, overlap=10)

        assert len(chunks) > 1
        assert chunks[0][-10:] == chunks[1][:10]

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
