"""Export service for generating novel output files."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chapter import chapter_service
from app.services.project import project_service


class ExportService:
    """Service for exporting project content to various formats."""

    async def export_txt(self, db: AsyncSession, project_id: UUID) -> str:
        """Export project as plain text."""
        project = await project_service.get(db, id=project_id)
        chapters = await chapter_service.get_by_project(db, project_id=project_id, limit=500)
        chapters = sorted(chapters, key=lambda c: c.chapter_number)

        lines = [project.name, "=" * len(project.name) * 2, ""]
        if project.summary:
            lines.extend([project.summary, ""])
        if project.story_outline:
            lines.extend(["项目大纲", "-" * 8, project.story_outline, ""])

        for ch in chapters:
            title = f"第{ch.chapter_number}章 {ch.title or ''}"
            lines.extend(["", title, "-" * len(title) * 2, ""])
            if ch.content:
                lines.append(ch.content)
            else:
                lines.append("（暂无内容）")

        return "\n".join(lines)

    async def export_markdown(self, db: AsyncSession, project_id: UUID) -> str:
        """Export project as Markdown."""
        project = await project_service.get(db, id=project_id)
        chapters = await chapter_service.get_by_project(db, project_id=project_id, limit=500)
        chapters = sorted(chapters, key=lambda c: c.chapter_number)

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
            if ch.content:
                lines.append(ch.content)
            else:
                lines.append("*（暂无内容）*")
            lines.append("")

        return "\n".join(lines)


export_service = ExportService()
