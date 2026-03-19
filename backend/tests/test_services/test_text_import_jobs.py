"""Tests for background text-import job runner."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select, update

from app.models.text_import_job import TextImportJob, TextImportJobStatus
from app.services.text_import import text_import_service
from app.services.text_import_jobs import TextImportJobRunner


class _SessionContext:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def __aenter__(self) -> Any:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _SessionFactory:
    def __init__(self, session: Any) -> None:
        self._session = session

    def __call__(self) -> _SessionContext:
        return _SessionContext(self._session)


@pytest.mark.asyncio
async def test_runner_requeues_processing_jobs(db_session) -> None:
    job = await text_import_service.create_background_job(
        db_session,
        text="第一章 起\n正文",
        project_name="恢复任务",
        genre="仙侠",
    )
    job.status = TextImportJobStatus.PROCESSING.value
    job.phase = "outline_extraction"
    job.progress = 0.42
    job.message = "处理中"
    await db_session.commit()

    runner = TextImportJobRunner(session_factory=_SessionFactory(db_session))
    await runner.requeue_processing_jobs()

    result = await db_session.execute(select(TextImportJob).where(TextImportJob.id == job.id))
    stored_job = result.scalar_one()

    assert stored_job.status == TextImportJobStatus.QUEUED.value
    assert stored_job.phase is None
    assert stored_job.progress == 0.0
    assert stored_job.message == "任务已重新排队等待处理"


@pytest.mark.asyncio
async def test_runner_processes_queued_jobs_in_order(db_session) -> None:
    first_job = await text_import_service.create_background_job(
        db_session,
        text="第一章 起\n正文",
        project_name="任务一",
        genre="仙侠",
    )
    second_job = await text_import_service.create_background_job(
        db_session,
        text="第一章 承\n正文",
        project_name="任务二",
        genre="仙侠",
    )
    await db_session.commit()

    processed_ids: list[str] = []

    async def processor(session: Any, job_id) -> None:
        processed_ids.append(str(job_id))
        await session.execute(
            update(TextImportJob)
            .where(TextImportJob.id == job_id)
            .values(
                status=TextImportJobStatus.COMPLETED.value,
                phase="completed",
                progress=1.0,
                message="完成",
            )
        )
        await session.commit()

    runner = TextImportJobRunner(
        session_factory=_SessionFactory(db_session),
        processor=processor,
    )
    processed = await runner.process_pending_jobs()

    assert processed == 2
    assert processed_ids == [str(first_job.id), str(second_job.id)]
