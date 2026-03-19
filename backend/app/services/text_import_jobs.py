"""Background job runner for large text imports."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy import select, update

from app.db import async_session_maker
from app.models.text_import_job import TextImportJob, TextImportJobStatus

logger = logging.getLogger(__name__)

TextImportJobProcessor = Callable[[Any, UUID], Awaitable[None]]


class TextImportJobRunner:
    """Single-worker background runner for large text-import jobs."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Any] = async_session_maker,
        processor: TextImportJobProcessor | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._processor = processor or self._default_processor
        self._task: asyncio.Task[None] | None = None
        self._wake_event = asyncio.Event()
        self._stop_event = asyncio.Event()

    async def _default_processor(self, db: Any, job_id: UUID) -> None:
        from app.services.text_import import text_import_service

        await text_import_service.process_background_job(db, job_id)

    def notify_new_job(self) -> None:
        """Wake the worker after a new job is queued."""
        self._wake_event.set()

    async def start(self) -> None:
        """Start the background worker if it is not already running."""
        if self._task is not None and not self._task.done():
            return

        self._wake_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        await self.requeue_processing_jobs()
        self._task = asyncio.create_task(self._run_loop(), name="text-import-job-runner")
        self.notify_new_job()

    async def stop(self) -> None:
        """Stop the background worker."""
        if self._task is None:
            return

        self._stop_event.set()
        self._wake_event.set()
        await self._task
        self._task = None

    async def requeue_processing_jobs(self) -> None:
        """Reset orphaned in-flight jobs so they can be retried from scratch."""
        async with self._session_factory() as session:
            await session.execute(
                update(TextImportJob)
                .where(TextImportJob.status == TextImportJobStatus.PROCESSING.value)
                .values(
                    status=TextImportJobStatus.QUEUED.value,
                    phase=None,
                    progress=0.0,
                    message="任务已重新排队等待处理",
                    error_detail=None,
                    preview_payload=None,
                    warnings=[],
                    failed_phases=[],
                    completed_at=None,
                )
            )
            await session.commit()

    async def process_next_job(self) -> bool:
        """Process the next queued job, if one exists."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(TextImportJob.id)
                .where(TextImportJob.status == TextImportJobStatus.QUEUED.value)
                .order_by(TextImportJob.created_at.asc())
                .limit(1)
            )
            job_id = result.scalar_one_or_none()
            if job_id is None:
                return False

            try:
                await self._processor(session, job_id)
            except Exception:  # pragma: no cover - defensive guard
                logger.exception("Background text-import job crashed: %s", job_id)
            return True

    async def process_pending_jobs(self) -> int:
        """Drain all currently queued jobs."""
        processed = 0
        while not self._stop_event.is_set():
            if not await self.process_next_job():
                break
            processed += 1
        return processed

    async def _run_loop(self) -> None:
        """Run the single-worker polling loop."""
        while not self._stop_event.is_set():
            processed = await self.process_pending_jobs()
            if processed > 0:
                continue

            try:
                await asyncio.wait_for(self._wake_event.wait(), timeout=5)
            except TimeoutError:
                continue
            finally:
                self._wake_event.clear()


text_import_job_runner = TextImportJobRunner()
