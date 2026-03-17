"""API tests for structured text import."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient

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
async def test_confirm_text_import_creates_project_records(client: AsyncClient) -> None:
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

    project_response = await client.get(f"/api/v1/projects/{project_id}")
    chapters_response = await client.get(f"/api/v1/chapters/project/{project_id}")
    volumes_response = await client.get(f"/api/v1/volumes/project/{project_id}")
    characters_response = await client.get(f"/api/v1/characters/project/{project_id}")
    settings_response = await client.get(f"/api/v1/world-settings/project/{project_id}")

    assert project_response.status_code == 200
    assert chapters_response.status_code == 200
    assert volumes_response.status_code == 200
    assert characters_response.status_code == 200
    assert settings_response.status_code == 200

    assert chapters_response.json()[0]["content"].startswith("第一章正文")
    assert volumes_response.json()[0]["title"] == "第一卷"
    assert characters_response.json()[0]["name"] == "陆沉"
    assert settings_response.json()[0]["name"] == "灵脉体系"
