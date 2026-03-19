"""Text import API routes."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import BadRequestException
from app.schemas.text_import import (
    TextImportConfirmRequest,
    TextImportJobResponse,
    TextImportResponse,
)
from app.services.text_import import text_import_service
from app.services.text_import_jobs import text_import_job_runner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["text-import"])
UPLOAD_CHUNK_SIZE = 1024 * 1024


@router.post("/import-text")
async def import_text_preview(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    project_name: str = Form(...),
    genre: str | None = Form(None),
) -> StreamingResponse:
    """Analyze an uploaded text file and stream progress + preview via SSE."""
    filename = (file.filename or "").strip()
    if not filename.lower().endswith((".txt", ".md", ".markdown")):
        raise BadRequestException("仅支持导入 .txt 或 .md 文本文件")

    chunks = bytearray()
    while True:
        chunk = await file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > text_import_service.MAX_FILE_SIZE:
            raise BadRequestException("上传文件过大，请控制在 64MB 以内")
    file_bytes = bytes(chunks)

    text, encoding = text_import_service.decode_bytes(file_bytes)
    if len(text_import_service._normalize_text(text)) < text_import_service.MIN_CHAR_COUNT:
        raise BadRequestException("文件内容过短，至少需要 500 字才能进行结构化导入")

    preview = text_import_service.inspect_text(
        text,
        project_name,
        genre,
        source_filename=filename or None,
        source_encoding=encoding,
    )
    structure_event = text_import_service.build_structure_detection_progress(preview)
    use_background_job = text_import_service.should_enqueue_background_job(preview.chapters)

    job_id: str | None = None
    if use_background_job:
        job = await text_import_service.create_background_job(
            db,
            text=text,
            project_name=project_name,
            genre=genre,
            source_filename=filename or None,
            source_encoding=encoding,
        )
        await db.commit()
        job_id = str(job.id)
        text_import_job_runner.notify_new_job()

    async def event_generator() -> AsyncIterator[str]:
        try:
            start_payload = {
                "phase": "structure_detection",
                "progress": 0.02,
                "message": "正在识别章节与卷结构",
                "data": {},
            }
            yield f"data: {json.dumps(start_payload, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps(structure_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"

            if use_background_job and job_id is not None:
                handoff_payload = {
                    "phase": "structure_detection",
                    "progress": structure_event.progress,
                    "message": "文本较大，已转入后台全量分析",
                    "data": {
                        "mode": "background_job",
                        "job_id": job_id,
                        "status_url": f"/api/v1/projects/import-text/jobs/{job_id}",
                        "chapters": len(preview.chapters),
                        "volumes": len(preview.volumes),
                        "warnings": list(preview.warnings),
                    },
                }
                yield f"data: {json.dumps(handoff_payload, ensure_ascii=False)}\n\n"
            else:
                async for event in text_import_service._analyze_detected_preview(preview):
                    payload = event.model_dump(mode="json")
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:  # pragma: no cover - defensive stream fallback
            logger.error("Text import analysis failed for %s: %s", filename, exc)
            error_payload = {
                "phase": "error",
                "progress": 1,
                "message": "文本分析失败",
                "data": {"detail": str(exc)},
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/import-text/jobs/{job_id}", response_model=TextImportJobResponse)
async def get_text_import_job(
    *,
    db: AsyncSession = Depends(get_db),
    job_id: str,
) -> TextImportJobResponse:
    """Get a background text-import job status and final preview."""
    job = await text_import_service.get_background_job(db, job_id)
    return text_import_service.build_background_job_response(job)


@router.post("/import-text/confirm", response_model=TextImportResponse)
async def confirm_text_import(
    *,
    db: AsyncSession = Depends(get_db),
    req: TextImportConfirmRequest,
) -> TextImportResponse:
    """Commit a previously analyzed preview into project records."""
    return await text_import_service.commit(db, req.preview)
