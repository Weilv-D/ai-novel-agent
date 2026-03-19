"""API tests for structured text import."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.schemas.text_import import TextImportPreview, TextImportProgress
from app.services.text_import import text_import_service


async def _fake_progress_stream() -> AsyncIterator[TextImportProgress]:
    preview = TextImportPreview(
        project_name="流式导入项目",
        genre="仙侠",
        summary="项目摘要",
        story_outline="项目总纲",
    )
    yield TextImportProgress(
        phase="structure_detection",
        progress=0.15,
        message="已识别 1 个章节",
        data={"chapters": 1},
    )
    yield TextImportProgress(
        phase="completed",
        progress=1.0,
        message="分析完成",
        data={"preview": preview.model_dump(mode="json")},
    )


@pytest.mark.asyncio
async def test_import_text_stream_returns_preview(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_analyze(*args, **kwargs) -> AsyncIterator[TextImportProgress]:
        async for item in _fake_progress_stream():
            yield item

    monkeypatch.setattr(text_import_service, "analyze", fake_analyze)

    response = await client.post(
        "/api/v1/projects/import-text",
        data={"project_name": "流式导入项目"},
        files={"file": ("novel.txt", "第一章\n" + ("正文内容" * 300), "text/plain")},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "data: " in response.text
    assert "流式导入项目" in response.text


@pytest.mark.asyncio
async def test_import_text_rejects_small_file(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/projects/import-text",
        data={"project_name": "太短文本"},
        files={"file": ("novel.txt", "只有一点点", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "文件内容过短，至少需要 500 字才能进行结构化导入"


@pytest.mark.asyncio
async def test_import_text_rejects_oversized_file(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(text_import_service, "MAX_FILE_SIZE", 1024)
    oversized_payload = "正文内容" * 300
    response = await client.post(
        "/api/v1/projects/import-text",
        data={"project_name": "超大文本"},
        files={"file": ("novel.txt", oversized_payload, "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "上传文件过大，请控制在 64MB 以内"


@pytest.mark.asyncio
async def test_confirm_text_import_creates_project_records(client: AsyncClient, db_session) -> None:
    preview = {
        "project_name": "接口导入项目",
        "genre": "玄幻",
        "summary": "项目摘要",
        "story_outline": "项目总纲",
        "volumes": [
            {
                "volume_number": 1,
                "title": "第一卷",
                "outline": "卷纲",
                "chapter_numbers": [1],
            }
        ],
        "chapters": [
            {
                "chapter_number": 1,
                "title": "第一章",
                "content": "第一章正文" * 40,
                "outline": "第一章章纲",
            }
        ],
        "characters": [
            {
                "name": "陆沉",
                "role": "主角",
                "profile": {"trait": "坚忍"},
                "relationships": {"师父": "引路人"},
            }
        ],
        "world_settings": [
            {
                "category": "magic_system",
                "name": "灵脉体系",
                "content": "修士依赖灵脉修行。",
            }
        ],
    }

    response = await client.post(
        "/api/v1/projects/import-text/confirm",
        json={"preview": preview},
    )

    assert response.status_code == 200
    payload = response.json()
    project_id = payload["project_id"]
    assert payload["project_name"] == "接口导入项目"
    assert payload["imported_counts"]["chapters"] == 1
    assert payload["imported_counts"]["memories"] == 1
    assert payload["imported_counts"]["dependencies"] == 4

    project_id_str = str(project_id)
    stored_project = (
        await db_session.execute(
            text("select name from projects where id = :project_id"),
            {"project_id": project_id_str},
        )
    ).mappings().one()
    stored_volumes = (
        await db_session.execute(
            text(
                """
                select title
                from volumes
                where project_id = :project_id
                order by volume_number asc
                """
            ),
            {"project_id": project_id_str},
        )
    )
    stored_chapters = (
        await db_session.execute(
            text(
                """
                select content
                from chapters
                where project_id = :project_id
                order by chapter_number asc
                """
            ),
            {"project_id": project_id_str},
        )
    )
    stored_characters = (
        await db_session.execute(
            text(
                """
                select name
                from characters
                where project_id = :project_id
                order by name asc
                """
            ),
            {"project_id": project_id_str},
        )
    )
    stored_settings = (
        await db_session.execute(
            text(
                """
                select name
                from world_settings
                where project_id = :project_id
                order by name asc
                """
            ),
            {"project_id": project_id_str},
        )
    )
    stored_memories = (
        await db_session.execute(
            text(
                """
                select memory_type, content, metadata
                from memories
                where project_id = :project_id
                order by created_at asc
                """
            ),
            {"project_id": project_id_str},
        )
    )
    stored_dependencies = (
        await db_session.execute(
            text(
                """
                select dependency_type
                from dependencies
                where project_id = :project_id
                order by created_at asc
                """
            ),
            {"project_id": project_id_str},
        )
    )
    volume_rows = stored_volumes.mappings().all()
    chapter_rows = stored_chapters.mappings().all()
    character_rows = stored_characters.mappings().all()
    setting_rows = stored_settings.mappings().all()
    memory_rows = stored_memories.mappings().all()
    dependency_rows = stored_dependencies.mappings().all()

    assert stored_project["name"] == "接口导入项目"
    assert chapter_rows[0]["content"].startswith("第一章正文")
    assert volume_rows[0]["title"] == "第一卷"
    assert character_rows[0]["name"] == "陆沉"
    assert setting_rows[0]["name"] == "灵脉体系"
    assert memory_rows[0]["memory_type"] == "episode"
    assert '"chapter_number": 1' in (memory_rows[0]["metadata"] or "")
    assert len(dependency_rows) == 4
