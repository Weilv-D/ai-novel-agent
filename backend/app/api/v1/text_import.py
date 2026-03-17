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
from app.schemas.text_import import TextImportConfirmRequest, TextImportResponse
from app.services.text_import import text_import_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["text-import"])


@router.post("/import-text")
async def import_text_preview(
    *,
    file: UploadFile = File(...),
    project_name: str = Form(...),
    genre: str | None = Form(None),
) -> StreamingResponse:
    """Analyze an uploaded text file and stream progress + preview via SSE."""
    filename = (file.filename or "").strip()
    if not filename.lower().endswith((".txt", ".md", ".markdown")):
        raise BadRequestException("仅支持导入 .txt 或 .md 文本文件")

    file_bytes = await file.read()
    if len(file_bytes) > text_import_service.MAX_FILE_SIZE:
        raise BadRequestException("上传文件过大，请控制在 15MB 以内")

    text, encoding = text_import_service.decode_bytes(file_bytes)
    if len(text_import_service._normalize_text(text)) < text_import_service.MIN_CHAR_COUNT:
        raise BadRequestException("文件内容过短，至少需要 500 字才能进行结构化导入")

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in text_import_service.analyze(
                text,
                project_name,
                genre,
                source_filename=filename or None,
                source_encoding=encoding,
            ):
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


@router.post("/import-text/confirm", response_model=TextImportResponse)
async def confirm_text_import(
    *,
    db: AsyncSession = Depends(get_db),
    req: TextImportConfirmRequest,
) -> TextImportResponse:
    """Commit a previously analyzed preview into project records."""
    return await text_import_service.commit(db, req.preview)
