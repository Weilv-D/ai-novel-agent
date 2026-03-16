"""API tests for the planner/executor agent workflow."""

import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.services.agent_workflow import agent_workflow_service


async def create_project(client: AsyncClient, *, name: str = "Test Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name, "genre": "fantasy"})
    assert response.status_code == 201
    return response.json()["id"]


async def create_thread(client: AsyncClient, project_id: str) -> str:
    response = await client.post("/api/v1/agent/threads", json={"project_id": project_id})
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(autouse=True)
def _agent_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow the planner service to run under test."""
    monkeypatch.setattr(agent_workflow_service.llm, "api_key", "test-key")


@pytest.mark.asyncio
async def test_create_character_run_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A planned run can create a new character and persist a snapshot."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "好的，我将创建一个名为「测试人物」的新角色。",
                        "operations": [
                            {
                                "tool_name": "create_character",
                                "description": "创建新人物",
                                "payload": {"name": "测试人物", "role": "protagonist"},
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建一个测试人物"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"
    assert run["operations"][0]["tool_name"] == "create_character"
    assert run["subtasks"]
    hook_names = [entry["hook_name"] for entry in run["meta"]["hook_trace"]]
    assert hook_names == ["PreCompact", "PrePlan", "SubagentStop"]

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "completed"

    characters_response = await client.get(f"/api/v1/characters/project/{project_id}")
    assert characters_response.status_code == 200
    characters = characters_response.json()
    assert len(characters) == 1
    assert characters[0]["name"] == "测试人物"


@pytest.mark.asyncio
async def test_update_character_run_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A planned run can update an existing character."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    create_response = await client.post(
        "/api/v1/characters",
        json={"name": "原人物", "role": "protagonist", "project_id": project_id},
    )
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "好的，我将更新人物信息。",
                        "operations": [
                            {
                                "tool_name": "update_character",
                                "description": "更新人物",
                                "payload": {
                                    "character_id": character_id,
                                    "updates": {"name": "更新后人物", "role": "antagonist"},
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "更新人物信息"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "completed"

    character_response = await client.get(f"/api/v1/characters/{character_id}")
    assert character_response.status_code == 200
    character = character_response.json()
    assert character["name"] == "更新后人物"
    assert character["role"] == "antagonist"


@pytest.mark.asyncio
async def test_create_world_setting_run_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A planned run can create a new world setting."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "好的，我将创建一个新的世界观设定。",
                        "operations": [
                            {
                                "tool_name": "create_world_setting",
                                "description": "创建世界观设定",
                                "payload": {
                                    "category": "magic_system",
                                    "name": "灵气体系",
                                    "content": "天地间存在灵气...",
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建一个世界观设定"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "completed"

    settings_response = await client.get(f"/api/v1/world-settings/project/{project_id}")
    assert settings_response.status_code == 200
    settings = settings_response.json()
    assert len(settings) == 1
    assert settings[0]["name"] == "灵气体系"


@pytest.mark.asyncio
async def test_update_world_setting_run_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A planned run can update an existing world setting."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    create_response = await client.post(
        "/api/v1/world-settings",
        json={"category": "magic_system", "name": "原设定", "content": "原内容", "project_id": project_id},
    )
    assert create_response.status_code == 201
    setting_id = create_response.json()["id"]

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "好的，我将更新世界观设定。",
                        "operations": [
                            {
                                "tool_name": "update_world_setting",
                                "description": "更新世界观设定",
                                "payload": {
                                    "setting_id": setting_id,
                                    "updates": {"name": "更新后设定", "content": "更新后内容"},
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "更新世界观设定"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "completed"

    setting_response = await client.get(f"/api/v1/world-settings/{setting_id}")
    assert setting_response.status_code == 200
    setting = setting_response.json()
    assert setting["name"] == "更新后设定"
    assert setting["content"] == "更新后内容"


@pytest.mark.asyncio
async def test_character_duplicate_name_fails(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating a character with duplicate name should fail domain verification."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    create_response = await client.post(
        "/api/v1/characters",
        json={"name": "林逸风", "role": "protagonist", "project_id": project_id},
    )
    assert create_response.status_code == 201

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我将创建一个同名人物。",
                        "operations": [
                            {
                                "tool_name": "create_character",
                                "description": "创建同名人物",
                                "payload": {"name": "林逸风", "role": "supporting"},
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建重复名称人物"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "failed"

    characters_response = await client.get(f"/api/v1/characters/project/{project_id}")
    characters = characters_response.json()
    assert len(characters) == 1


@pytest.mark.asyncio
async def test_character_invalid_age_fails(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating a character with invalid age should fail domain verification."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我将创建一个年龄为负数的人物。",
                        "operations": [
                            {
                                "tool_name": "create_character",
                                "description": "创建非法年龄人物",
                                "payload": {
                                    "name": "测试人物",
                                    "role": "supporting",
                                    "profile": {"age": -5},
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建非法年龄人物"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "failed"


@pytest.mark.asyncio
async def test_world_setting_duplicate_name_fails(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating a world setting with duplicate name in same category should fail."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    create_response = await client.post(
        "/api/v1/world-settings",
        json={"category": "magic_system", "name": "灵气体系", "content": "原内容", "project_id": project_id},
    )
    assert create_response.status_code == 201

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我将创建一个同名设定。",
                        "operations": [
                            {
                                "tool_name": "create_world_setting",
                                "description": "创建同名设定",
                                "payload": {
                                    "category": "magic_system",
                                    "name": "灵气体系",
                                    "content": "新内容",
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建重复名称设定"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "failed"


@pytest.mark.asyncio
async def test_world_setting_empty_content_fails(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating a world setting with empty content should fail at service layer."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我将创建一个内容为空的设定。",
                        "operations": [
                            {
                                "tool_name": "create_world_setting",
                                "description": "创建空内容设定",
                                "payload": {
                                    "category": "other",
                                    "name": "空设定",
                                    "content": "   ",
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建空内容设定"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "failed"
    assert confirm_data["run"]["operations"][0]["status"] == "failed"
    assert "empty" in confirm_data["run"]["operations"][0]["error_message"].lower() or "content" in confirm_data["run"]["operations"][0]["error_message"].lower()


@pytest.mark.asyncio
async def test_character_empty_name_fails(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating a character with empty name should fail at schema validation."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我将创建一个名称为空的人物。",
                        "operations": [
                            {
                                "tool_name": "create_character",
                                "description": "创建空名称人物",
                                "payload": {"name": "   ", "role": "supporting"},
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建空名称人物"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_existing_chapter_scene_verification_still_works(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing chapter/scene domain verification should not regress."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    chapter_response = await client.post(
        "/api/v1/chapters",
        json={"chapter_number": 1, "title": "第一章", "project_id": project_id},
    )
    assert chapter_response.status_code == 201

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我将创建一个重复章节号。",
                        "operations": [
                            {
                                "tool_name": "create_chapter",
                                "description": "创建重复章节",
                                "payload": {"chapter_number": 1, "title": "重复章节"},
                            }
                        ],
                    }
                ),
            },
        ),
    )
    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建重复章节"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["status"] == "awaiting_confirmation"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["run"]["status"] == "failed"
    operation = confirm_data["run"]["operations"][0]
    assert "already exists" in (operation["error_message"] or "")


@pytest.mark.asyncio
async def test_update_project_outline_run_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A planned run can update the project-level story outline."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我会先补全项目大纲。",
                        "operations": [
                            {
                                "tool_name": "update_project_outline",
                                "description": "补充项目大纲",
                                "payload": {
                                    "updates": {
                                        "story_outline": "项目大纲：主角从入局到登顶，分三卷完成身份跃迁。"
                                    }
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )

    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "补一个项目大纲"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["operations"][0]["tool_name"] == "update_project_outline"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    assert confirm_response.json()["run"]["status"] == "completed"

    project_response = await client.get(f"/api/v1/projects/{project_id}")
    assert project_response.status_code == 200
    assert "身份跃迁" in project_response.json()["story_outline"]


@pytest.mark.asyncio
async def test_create_volume_run_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A planned run can create a volume under the current project."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我会创建第一卷细纲。",
                        "operations": [
                            {
                                "tool_name": "create_volume",
                                "description": "创建第一卷",
                                "payload": {
                                    "volume_number": 1,
                                    "title": "第一卷 北地试锋",
                                    "outline": "第一卷聚焦入局试探、资源争夺与卷末局势翻转。",
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )

    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建第一卷细纲"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["operations"][0]["tool_name"] == "create_volume"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    assert confirm_response.json()["run"]["status"] == "completed"

    volumes_response = await client.get(f"/api/v1/volumes/project/{project_id}")
    assert volumes_response.status_code == 200
    volumes = volumes_response.json()
    assert len(volumes) == 1
    assert volumes[0]["title"] == "第一卷 北地试锋"


@pytest.mark.asyncio
async def test_update_volume_run_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A planned run can update an existing volume outline."""
    project_id = await create_project(client)
    thread_id = await create_thread(client, project_id)

    volume_response = await client.post(
        "/api/v1/volumes",
        json={"project_id": project_id, "volume_number": 1, "title": "第一卷", "outline": "旧卷纲"},
    )
    assert volume_response.status_code == 201
    volume_id = volume_response.json()["id"]

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "assistant_message": "我会更新卷细纲。",
                        "operations": [
                            {
                                "tool_name": "update_volume",
                                "description": "更新第一卷细纲",
                                "payload": {
                                    "volume_id": volume_id,
                                    "updates": {
                                        "outline": "新卷纲：加入支线网络、因果链升级和卷末悬念。"
                                    },
                                },
                            }
                        ],
                    }
                ),
            },
        ),
    )

    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "更新第一卷细纲"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["operations"][0]["tool_name"] == "update_volume"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    assert confirm_response.json()["run"]["status"] == "completed"

    updated_volume_response = await client.get(f"/api/v1/volumes/{volume_id}")
    assert updated_volume_response.status_code == 200
    assert "支线网络" in updated_volume_response.json()["outline"]
