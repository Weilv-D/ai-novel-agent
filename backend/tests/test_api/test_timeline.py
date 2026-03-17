"""Tests for timeline API routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.chapter import Chapter, Scene, Volume
from app.models.memory import Memory
from app.models.project import Project


@pytest.mark.asyncio
async def test_project_timeline_aggregates_chapters_and_episode_memories(
    client: AsyncClient,
    db_session,
) -> None:
    """Timeline should order chapters and attach event memories by chapter or scene reference."""
    project = Project(
        id=uuid.uuid4(),
        name="山海夜行",
        agent_profile_id="default",
        meta={"agent_profile_id": "default"},
    )
    volume_one = Volume(id=uuid.uuid4(), project_id=project.id, volume_number=1, title="卷一", outline=None, notes=None)
    volume_two = Volume(id=uuid.uuid4(), project_id=project.id, volume_number=2, title="卷二", outline=None, notes=None)
    chapter_one = Chapter(
        id=uuid.uuid4(),
        project_id=project.id,
        volume_id=volume_one.id,
        chapter_number=1,
        title="入山",
        outline="进入山门",
        content=None,
        status="draft",
        notes=None,
    )
    chapter_two = Chapter(
        id=uuid.uuid4(),
        project_id=project.id,
        volume_id=volume_one.id,
        chapter_number=2,
        title="夜雨",
        outline="雨夜追踪",
        content=None,
        status="writing",
        notes=None,
    )
    chapter_three = Chapter(
        id=uuid.uuid4(),
        project_id=project.id,
        volume_id=volume_two.id,
        chapter_number=1,
        title="归城",
        outline="回到都城",
        content=None,
        status="completed",
        notes=None,
    )
    scene_one = Scene(
        id=uuid.uuid4(),
        chapter_id=chapter_one.id,
        scene_order=1,
        pov_character_id=None,
        location="山门",
        content=None,
        meta={},
    )
    scene_two = Scene(
        id=uuid.uuid4(),
        chapter_id=chapter_one.id,
        scene_order=2,
        pov_character_id=None,
        location="偏殿",
        content=None,
        meta={},
    )
    base_time = datetime(2026, 3, 17, 9, 0, tzinfo=UTC)
    memory_scene = Memory(
        id=uuid.uuid4(),
        project_id=project.id,
        memory_type="episode",
        content="主角在山门外第一次见到守夜人。",
        embedding=None,
        meta={"scene_id": str(scene_one.id), "title": "山门初遇"},
        created_at=base_time,
        updated_at=base_time,
    )
    memory_chapter = Memory(
        id=uuid.uuid4(),
        project_id=project.id,
        memory_type="episode",
        content="偏殿里发现了失踪卷宗。",
        embedding=None,
        meta={"chapter_id": str(chapter_one.id), "scene_order": 2},
        created_at=base_time + timedelta(minutes=1),
        updated_at=base_time + timedelta(minutes=1),
    )
    memory_nested = Memory(
        id=uuid.uuid4(),
        project_id=project.id,
        memory_type="episode",
        content="夜雨中有人尾随。",
        embedding=None,
        meta={"context": {"chapter": 2}, "summary": "尾随事件"},
        created_at=base_time + timedelta(minutes=2),
        updated_at=base_time + timedelta(minutes=2),
    )
    memory_loose = Memory(
        id=uuid.uuid4(),
        project_id=project.id,
        memory_type="episode",
        content="一条尚未归档到章节的传闻。",
        embedding=None,
        meta={"label": "游离线索"},
        created_at=base_time + timedelta(minutes=3),
        updated_at=base_time + timedelta(minutes=3),
    )
    ignored_fact = Memory(
        id=uuid.uuid4(),
        project_id=project.id,
        memory_type="fact",
        content="护山阵法只在子夜开启。",
        embedding=None,
        meta={"chapter_id": str(chapter_one.id)},
        created_at=base_time + timedelta(minutes=4),
        updated_at=base_time + timedelta(minutes=4),
    )

    db_session.add_all(
        [
            project,
            volume_one,
            volume_two,
            chapter_one,
            chapter_two,
            chapter_three,
            scene_one,
            scene_two,
            memory_scene,
            memory_chapter,
            memory_nested,
            memory_loose,
            ignored_fact,
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}/timeline")

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == str(project.id)
    assert [chapter["title"] for chapter in data["chapters"]] == ["入山", "夜雨", "归城"]
    assert data["chapters"][0]["volume"]["title"] == "卷一"
    assert data["chapters"][0]["event_count"] == 2
    assert [event["title"] for event in data["chapters"][0]["events"]] == ["山门初遇", "偏殿里发现了失踪卷宗。"]
    assert data["chapters"][0]["events"][1]["scene_order"] == 2
    assert data["chapters"][1]["event_count"] == 1
    assert data["chapters"][1]["events"][0]["summary"] == "尾随事件"
    assert data["chapters"][2]["event_count"] == 0
    assert len(data["unassigned_events"]) == 1
    assert data["unassigned_events"][0]["title"] == "游离线索"
    assert data["total_events"] == 4
