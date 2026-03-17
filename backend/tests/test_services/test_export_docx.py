"""DOCX export tests."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.export import export_service

docx = pytest.importorskip("docx")


class TestExportDocx:
    """Tests for DOCX export output."""

    @pytest.mark.asyncio
    async def test_export_docx_includes_project_outline_and_chapters(self) -> None:
        """DOCX export should preserve project headings and chapter content."""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.name = "墨雨录"
        mock_project.summary = "一部测试小说"
        mock_project.story_outline = "第一幕\n第二幕"

        chapter = MagicMock()
        chapter.chapter_number = 1
        chapter.title = "雨夜"
        chapter.outline = "主角入场"
        chapter.content = "<p>第一段</p><p>第二段<br />第三句</p><ul><li>线索</li></ul>"

        with patch("app.services.export.project_service.get", new_callable=AsyncMock) as mock_get_project:
            with patch("app.services.export.chapter_service.get_by_project", new_callable=AsyncMock) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = [chapter]

                content = await export_service.export_docx(mock_db, mock_project.id)

        document = docx.Document(BytesIO(content))
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text]

        assert "墨雨录" in paragraphs
        assert "项目大纲" in paragraphs
        assert "第一幕" in paragraphs
        assert "第1章 雨夜" in paragraphs
        assert "主角入场" in paragraphs
        assert "第一段" in paragraphs
        assert "第二段" in paragraphs
        assert "第三句" in paragraphs
        assert "- 线索" in paragraphs

    @pytest.mark.asyncio
    async def test_export_txt_strips_rich_text_tags(self) -> None:
        """TXT export should convert stored HTML fragments into readable plain text."""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.name = "墨雨录"
        mock_project.summary = None
        mock_project.story_outline = None

        chapter = MagicMock()
        chapter.chapter_number = 2
        chapter.title = "回声"
        chapter.content = "<h2>小节</h2><p>段落一</p><p>段落二</p><ul><li>伏笔</li></ul>"

        with patch("app.services.export.project_service.get", new_callable=AsyncMock) as mock_get_project:
            with patch("app.services.export.chapter_service.get_by_project", new_callable=AsyncMock) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = [chapter]

                content = await export_service.export_txt(mock_db, mock_project.id)

        assert "<p>" not in content
        assert "小节" in content
        assert "段落一" in content
        assert "段落二" in content
        assert "- 伏笔" in content
