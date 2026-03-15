"""Project package export/import API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.project_package import ProjectImportResponse
from app.services.project_package import project_package_service

router = APIRouter(prefix="/projects", tags=["project-package"])


@router.get("/{project_id}/package")
async def export_project_package(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
) -> Response:
    """Export a project as a downloadable zip package."""
    zip_bytes, filename = await project_package_service.export_package(
        db,
        project_id=project_id,
    )
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=ProjectImportResponse)
async def import_project_package(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    new_name: str | None = None,
) -> ProjectImportResponse:
    """Import a project from an uploaded zip package.

    Creates a new project as a copy of the exported project.
    """
    zip_bytes = await file.read()
    return await project_package_service.import_package(
        db,
        zip_bytes=zip_bytes,
        new_name=new_name,
    )
