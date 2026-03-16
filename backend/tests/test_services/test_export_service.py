"""Tests for Export Service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.chapter import Chapter
from app.models.project import Project
from app.services.chapter import chapter_service
from app.services.export import export_service
from app.services.project import project_service


class TestExportService:
    """Tests for ExportService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        db = MagicMock()
        return db

    @pytest.mark.asyncio
    async def test_export_txt_empty_project(self, mock_db_session):
        """Test exporting empty project to TXT format."""
        project_id = uuid.uuid4()

        mock_project = MagicMock(spec=Project)
        mock_project.name = "Empty Project"
        mock_project.summary = None
        mock_project.story_outline = None

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = []

                content = await export_service.export_txt(mock_db_session, str(project_id))

                assert "Empty Project" in content
                assert "暂无内容" not in content

    @pytest.mark.asyncio
    async def test_export_txt_with_chapters(self, mock_db_session):
        """Test exporting project with chapters to TXT format."""
        project_id = uuid.uuid4()

        mock_project = MagicMock(spec=Project)
        mock_project.name = "Test Novel"
        mock_project.summary = "A test novel summary"
        mock_project.story_outline = None

        chapter1 = MagicMock(spec=Chapter)
        chapter1.chapter_number = 1
        chapter1.title = "Beginning"
        chapter1.content = "Chapter 1 content here."

        chapter2 = MagicMock(spec=Chapter)
        chapter2.chapter_number = 2
        chapter2.title = "Middle"
        chapter2.content = "Chapter 2 content here."

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = [chapter1, chapter2]

                content = await export_service.export_txt(mock_db_session, str(project_id))

                assert "Test Novel" in content
                assert "A test novel summary" in content
                assert "第1章 Beginning" in content
                assert "Chapter 1 content here" in content
                assert "第2章 Middle" in content
                assert "Chapter 2 content here" in content

    @pytest.mark.asyncio
    async def test_export_txt_chapters_sorted_by_number(self, mock_db_session):
        """Test that chapters are sorted by chapter number."""
        project_id = uuid.uuid4()

        mock_project = MagicMock()
        mock_project.name = "Sorted Novel"
        mock_project.summary = None
        mock_project.story_outline = None

        chapter3 = MagicMock(spec=Chapter)
        chapter3.chapter_number = 3
        chapter3.title = "Third"
        chapter3.content = "Third content"

        chapter1 = MagicMock(spec=Chapter)
        chapter1.chapter_number = 1
        chapter1.title = "First"
        chapter1.content = "First content"

        chapter2 = MagicMock(spec=Chapter)
        chapter2.chapter_number = 2
        chapter2.title = "Second"
        chapter2.content = "Second content"

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = [chapter3, chapter1, chapter2]

                content = await export_service.export_txt(mock_db_session, str(project_id))

                first_pos = content.find("第1章")
                second_pos = content.find("第2章")
                third_pos = content.find("第3章")

                assert first_pos < second_pos < third_pos

    @pytest.mark.asyncio
    async def test_export_txt_no_content_shows_placeholder(self, mock_db_session):
        """Test that chapters without content show placeholder."""
        project_id = uuid.uuid4()

        mock_project = MagicMock()
        mock_project.name = "Draft Novel"
        mock_project.summary = None
        mock_project.story_outline = None

        chapter = MagicMock(spec=Chapter)
        chapter.chapter_number = 1
        chapter.title = "Draft Chapter"
        chapter.content = None

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = [chapter]

                content = await export_service.export_txt(mock_db_session, str(project_id))

                assert "（暂无内容）" in content

    @pytest.mark.asyncio
    async def test_export_markdown_empty_project(self, mock_db_session):
        """Test exporting empty project to Markdown format."""
        project_id = uuid.uuid4()

        mock_project = MagicMock(spec=Project)
        mock_project.name = "Empty Project"
        mock_project.summary = None
        mock_project.story_outline = None

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = []

                content = await export_service.export_markdown(mock_db_session, str(project_id))

                assert "# Empty Project" in content

    @pytest.mark.asyncio
    async def test_export_markdown_with_chapters(self, mock_db_session):
        """Test exporting project with chapters to Markdown format."""
        project_id = uuid.uuid4()

        mock_project = MagicMock(spec=Project)
        mock_project.name = "Test Novel"
        mock_project.summary = "A test novel"
        mock_project.story_outline = None

        chapter = MagicMock(spec=Chapter)
        chapter.chapter_number = 1
        chapter.title = "The Beginning"
        chapter.outline = "Intro outline"
        chapter.content = "Chapter content."

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = [chapter]

                content = await export_service.export_markdown(mock_db_session, str(project_id))

                assert "# Test Novel" in content
                assert "> A test novel" in content
                assert "## 第1章 The Beginning" in content
                assert "*Intro outline*" in content
                assert "Chapter content." in content

    @pytest.mark.asyncio
    async def test_export_markdown_chapters_sorted(self, mock_db_session):
        """Test that markdown chapters are sorted by chapter number."""
        project_id = uuid.uuid4()

        mock_project = MagicMock(spec=Project)
        mock_project.name = "Sorted Novel"
        mock_project.story_outline = None

        chapter2 = MagicMock(spec=Chapter)
        chapter2.chapter_number = 2
        chapter2.title = "Second"
        chapter2.outline = None
        chapter2.content = "Content 2"

        chapter1 = MagicMock(spec=Chapter)
        chapter1.chapter_number = 1
        chapter1.title = "First"
        chapter1.outline = None
        chapter1.content = "Content 1"

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = [chapter2, chapter1]

                content = await export_service.export_markdown(mock_db_session, str(project_id))

                first_pos = content.find("## 第1章")
                second_pos = content.find("## 第2章")

                assert first_pos < second_pos

    @pytest.mark.asyncio
    async def test_export_markdown_no_content_shows_placeholder(self, mock_db_session):
        """Test that markdown chapters without content show placeholder."""
        project_id = uuid.uuid4()

        mock_project = MagicMock(spec=Project)
        mock_project.name = "Draft Novel"
        mock_project.summary = None
        mock_project.story_outline = None

        chapter = MagicMock(spec=Chapter)
        chapter.chapter_number = 1
        chapter.title = "Empty Chapter"
        chapter.outline = None
        chapter.content = None

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = [chapter]

                content = await export_service.export_markdown(mock_db_session, str(project_id))

                assert "（暂无内容）" in content

    @pytest.mark.asyncio
    async def test_export_txt_with_summary(self, mock_db_session):
        """Test TXT export includes project summary."""
        project_id = uuid.uuid4()

        mock_project = MagicMock(spec=Project)
        mock_project.name = "My Novel"
        mock_project.summary = "This is a novel summary."
        mock_project.story_outline = None

        with patch.object(project_service, "get", new_callable=AsyncMock) as mock_get_project:
            with patch.object(
                chapter_service, "get_by_project", new_callable=AsyncMock
            ) as mock_get_chapters:
                mock_get_project.return_value = mock_project
                mock_get_chapters.return_value = []

                content = await export_service.export_txt(mock_db_session, str(project_id))

                assert "This is a novel summary." in content
