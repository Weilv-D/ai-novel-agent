"""Export service for generating novel output files."""

import re
from html.parser import HTMLParser
from io import BytesIO
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceUnavailableException
from app.models.chapter import Chapter
from app.models.project import Project
from app.services.chapter import chapter_service
from app.services.project import project_service


class ExportService:
    """Service for exporting project content to various formats."""

    CHAPTER_EXPORT_BATCH_SIZE = 200

    @staticmethod
    def _looks_like_html(text: str) -> bool:
        return bool(re.search(r"</?[a-z][^>]*>", text, flags=re.IGNORECASE))

    @classmethod
    def _rich_text_to_plain_text(cls, text: str) -> str:
        if not text:
            return ""

        if not cls._looks_like_html(text):
            return text.strip()

        parser = _HTMLToPlainTextParser()
        parser.feed(text)
        parser.close()
        return parser.get_text()

    async def _load_project_content(self, db: AsyncSession, project_id: UUID) -> tuple[Project, list[Chapter]]:
        """Load a project and its chapters ordered by chapter number."""
        project = await project_service.get(db, id=project_id)
        chapters: list[Chapter] = []
        skip = 0
        while True:
            batch = await chapter_service.get_by_project(
                db,
                project_id=project_id,
                skip=skip,
                limit=self.CHAPTER_EXPORT_BATCH_SIZE,
            )
            chapters.extend(batch)
            if len(batch) < self.CHAPTER_EXPORT_BATCH_SIZE:
                break
            skip += len(batch)
        return project, sorted(chapters, key=lambda chapter: chapter.chapter_number)

    @staticmethod
    def _append_multiline_paragraphs(document: Any, text: str) -> None:
        """Append text to a docx document while preserving line breaks."""
        for line in text.splitlines():
            document.add_paragraph(line)
        if not text.splitlines():
            document.add_paragraph("")

    async def export_txt(self, db: AsyncSession, project_id: UUID) -> str:
        """Export project as plain text."""
        project, chapters = await self._load_project_content(db, project_id)

        lines = [project.name, "=" * len(project.name) * 2, ""]
        if project.summary:
            lines.extend([project.summary, ""])
        if project.story_outline:
            lines.extend(["项目大纲", "-" * 8, project.story_outline, ""])

        for ch in chapters:
            title = f"第{ch.chapter_number}章 {ch.title or ''}"
            lines.extend(["", title, "-" * len(title) * 2, ""])
            chapter_content = self._rich_text_to_plain_text(ch.content or "")
            if chapter_content:
                lines.append(chapter_content)
            else:
                lines.append("（暂无内容）")

        return "\n".join(lines)

    async def export_markdown(self, db: AsyncSession, project_id: UUID) -> str:
        """Export project as Markdown."""
        project, chapters = await self._load_project_content(db, project_id)

        lines = [f"# {project.name}", ""]
        if project.summary:
            lines.extend([f"> {project.summary}", ""])
        if project.story_outline:
            lines.extend(["## 项目大纲", "", project.story_outline, ""])

        for ch in chapters:
            title = ch.title or ""
            lines.extend([f"## 第{ch.chapter_number}章 {title}", ""])
            if ch.outline:
                lines.extend([f"*{ch.outline}*", ""])
            chapter_content = self._rich_text_to_plain_text(ch.content or "")
            if chapter_content:
                lines.append(chapter_content)
            else:
                lines.append("*（暂无内容）*")
            lines.append("")

        return "\n".join(lines)

    async def export_docx(self, db: AsyncSession, project_id: UUID) -> bytes:
        """Export project as a DOCX document."""
        try:
            from docx import Document
        except ImportError as exc:
            raise ServiceUnavailableException("DOCX export dependency not installed") from exc

        project, chapters = await self._load_project_content(db, project_id)

        document = Document()
        document.core_properties.title = project.name
        document.add_heading(project.name, level=0)

        if project.summary:
            self._append_multiline_paragraphs(document, project.summary)

        if project.story_outline:
            document.add_heading("项目大纲", level=1)
            self._append_multiline_paragraphs(document, project.story_outline)

        for chapter in chapters:
            title = chapter.title or ""
            document.add_heading(f"第{chapter.chapter_number}章 {title}".strip(), level=1)
            if chapter.outline:
                outline_paragraph = document.add_paragraph()
                outline_paragraph.add_run(chapter.outline).italic = True
            chapter_content = self._rich_text_to_plain_text(chapter.content or "")
            if chapter_content:
                self._append_multiline_paragraphs(document, chapter_content)
            else:
                document.add_paragraph("（暂无内容）")

        buffer = BytesIO()
        document.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()


export_service = ExportService()


class _HTMLToPlainTextParser(HTMLParser):
    """Convert a limited HTML fragment into readable plain text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        normalized = tag.lower()
        if normalized == "br":
            self._append_newline()
        elif normalized == "li":
            self._append_block_break()
            self._parts.append("- ")
        elif normalized in {"p", "div", "section", "article", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._append_block_break()

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"p", "div", "section", "article", "blockquote", "pre", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._append_block_break()

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _append_block_break(self) -> None:
        if not self._parts:
            return
        tail = self._parts[-1]
        if tail.endswith("\n\n"):
            return
        if tail.endswith("\n"):
            self._parts.append("\n")
            return
        self._parts.append("\n\n")

    def _append_newline(self) -> None:
        if not self._parts:
            return
        if not self._parts[-1].endswith("\n"):
            self._parts.append("\n")
