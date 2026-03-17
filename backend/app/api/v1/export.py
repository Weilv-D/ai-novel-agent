"""Export API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import BadRequestException
from app.services.export import export_service

router = APIRouter(prefix="/projects", tags=["export"])


@router.get("/{project_id}/export")
async def export_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    format: str = Query("txt", pattern="^(txt|markdown|docx)$"),
) -> Response:
    """Export project content as TXT, Markdown, or DOCX."""
    if format == "txt":
        content = await export_service.export_txt(db, project_id)
        filename = "novel.txt"
        media_type = "text/plain; charset=utf-8"
        return PlainTextResponse(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    elif format == "markdown":
        content = await export_service.export_markdown(db, project_id)
        filename = "novel.md"
        media_type = "text/markdown; charset=utf-8"
        return PlainTextResponse(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    elif format == "docx":
        docx_content = await export_service.export_docx(db, project_id)
        filename = "novel.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return Response(
            content=docx_content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        raise BadRequestException(f"Unsupported format: {format}")
