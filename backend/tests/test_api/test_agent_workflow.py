"""API tests for the planner/executor agent workflow."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

import app.services.agent_workflow as agent_workflow_module
from app.services.agent_workflow import PlannedSubtaskSpec, agent_workflow_service


def planner_response(
    *,
    assistant_message: str,
    summary: str,
    operations: list[dict[str, object]],
    warning_message: str | None = None,
    subtasks: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build a fake planner response payload."""
    return {
        "content": json.dumps(
            {
                "assistant_message": assistant_message,
                "summary": summary,
                "warning_message": warning_message,
                "operations": operations,
                "subtasks": subtasks or [],
            },
            ensure_ascii=False,
        )
    }


async def create_project(client: AsyncClient, *, name: str = "Agent Test Project") -> str:
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
            return_value=planner_response(
                assistant_message="我会先创建人物卡，再等你确认执行。",
                summary="创建人物 林霁",
                operations=[
                    {
                        "tool_name": "create_character",
                        "description": "创建新人物林霁",
                        "reason": "用户要求新增主要人物",
                        "payload": {
                            "name": "林霁",
                            "role": "主角",
                            "profile": {"personality": "冷静克制"},
                        },
                    }
                ],
            )
        ),
    )

    message_response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建一个冷静克制的主角，名字叫林霁"},
    )
    assert message_response.status_code == 200
    run = message_response.json()["run"]
    assert run["status"] == "awaiting_confirmation"
    assert run["operations"][0]["tool_name"] == "create_character"
    assert run["subtasks"]
    hook_names = [entry["hook_name"] for entry in run["meta"]["hook_trace"]]
    assert hook_names == ["PreCompact", "PrePlan", "SubagentStop"]
    assert run["meta"]["skill_snapshot"]["planner"]["name"] == "novel-agent-planner"
    assert run["meta"]["skill_snapshot"]["profile_id"] == "default"
    assert run["meta"]["skill_snapshot"]["operations"][0]["tool_name"] == "create_character"
    permission_matrix = run["execution_contract"]
    risk_summary = run["risk_summary"]
    assert permission_matrix["registry_version"] == "2026-03-15.1"
    assert risk_summary["policy_version"] == "2026-03-15.2"
    assert risk_summary["overall_risk_level"] == "low"
    assert risk_summary["confirmation_gate"] == "single"
    assert [policy["policy_id"] for policy in risk_summary["applied_policies"]] == ["create_only"]
    assert risk_summary["high_risk_operation_positions"] == []
    assert permission_matrix["phases"][0]["phase"] == "plan"
    assert permission_matrix["phases"][0]["allowed_permission_levels"] == ["read_search"]
    assert "list_project_characters" in permission_matrix["phases"][0]["tool_scope"]
    assert permission_matrix["phases"][0]["capabilities"][0]["capability_id"] == "project_inventory"
    assert permission_matrix["phases"][0]["capabilities"][0]["policy"]["execution_phase"] == "plan"
    assert permission_matrix["phases"][0]["capabilities"][0]["execution_record"]["status"] == "completed"
    assert permission_matrix["phases"][0]["capabilities"][0]["execution_record"]["source_role"] == "researcher"
    assert [unit["role"] for unit in permission_matrix["phases"][0]["child_units"]] == ["planner", "researcher"]
    assert permission_matrix["phases"][0]["child_units"][1]["capability_ids"] == [
        "project_inventory",
        "focused_object_resolution",
        "checkpoint_context",
    ]
    assert permission_matrix["phases"][1]["phase"] == "build"
    assert permission_matrix["phases"][1]["allowed_permission_levels"] == ["standard_write"]
    assert permission_matrix["phases"][1]["capabilities"][0]["policy"]["source_role"] == "executor"
    assert permission_matrix["phases"][1]["capabilities"][0]["execution_record"]["status"] == "planned"
    assert [unit["role"] for unit in permission_matrix["phases"][1]["child_units"]] == ["continuity", "executor"]
    assert permission_matrix["phases"][1]["child_units"][0]["stage"] == "pre_execution"
    assert permission_matrix["phases"][1]["child_units"][1]["capability_ids"] == ["operation_execution"]
    planner_subtask = next(subtask for subtask in run["subtasks"] if subtask["role"] == "planner")
    planner_trace = planner_subtask["child_trace"]
    assert planner_subtask["meta"]["retry_strategy"] == "service_only"
    assert planner_trace["depends_on"] == []
    assert planner_trace["attempts"][0]["source"] == "service"
    assert planner_trace["attempts"][0]["accepted"] is True
    researcher_subtask = next(subtask for subtask in run["subtasks"] if subtask["role"] == "researcher")
    assert "resolve_current_character" in researcher_subtask["child_trace"]["tool_scope"]
    assert researcher_subtask["child_trace"]["execution_phase"] == "plan"

    confirm_response = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm_response.status_code == 200
    confirmed_run = confirm_response.json()["run"]
    assert confirmed_run["status"] == "completed"
    assert confirmed_run["meta"]["hook_trace"][-1]["hook_name"] == "RunStop"
    assert confirmed_run["meta"]["hook_trace"][-1]["status"] == "completed"

    characters_response = await client.get(f"/api/v1/characters/project/{project_id}")
    assert characters_response.status_code == 200
    characters = characters_response.json()
    assert len(characters) == 1
    assert characters[0]["name"] == "林霁"

    snapshots_response = await client.get(f"/api/v1/snapshots?project_id={project_id}")
    assert snapshots_response.status_code == 200
    snapshots = snapshots_response.json()
    assert len(snapshots) == 1
    assert snapshots[0]["target_type"] == "character"


@pytest.mark.asyncio
async def test_revision_supersedes_previous_run_and_updates_setting(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new message replaces a pending run and executes the revised plan."""
    project_id = await create_project(client, name="World Test")
    thread_id = await create_thread(client, project_id)

    setting_response = await client.post(
        "/api/v1/world-settings",
        json={
            "project_id": project_id,
            "category": "rules",
            "name": "灵脉规则",
            "content": "旧设定",
        },
    )
    assert setting_response.status_code == 201

    planner_generate = AsyncMock(
        side_effect=[
            planner_response(
                assistant_message="我会改灵脉规则。",
                summary="修改设定 灵脉规则",
                operations=[
                    {
                        "tool_name": "update_world_setting",
                        "description": "补强灵脉规则",
                        "reason": "用户要求修订设定",
                        "payload": {
                            "setting_name": "灵脉规则",
                            "updates": {"content": "新设定 v1"},
                        },
                    }
                ],
            ),
            planner_response(
                assistant_message="我会把设定调得更冷峻。",
                summary="再次修改设定 灵脉规则",
                operations=[
                    {
                        "tool_name": "update_world_setting",
                        "description": "把设定改得更冷峻",
                        "reason": "用户进一步细化要求",
                        "payload": {
                            "setting_name": "灵脉规则",
                            "updates": {"content": "新设定 v2，更冷峻"},
                        },
                    }
                ],
            ),
        ]
    )
    monkeypatch.setattr(agent_workflow_service.llm, "generate", planner_generate)

    first = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "把灵脉规则改得更严格"},
    )
    assert first.status_code == 200
    first_run_id = first.json()["run"]["id"]

    second = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "再改得更冷峻一点"},
    )
    assert second.status_code == 200
    second_run_id = second.json()["run"]["id"]

    first_run = await client.get(f"/api/v1/agent/runs/{first_run_id}")
    assert first_run.status_code == 200
    assert first_run.json()["status"] == "superseded"

    confirm = await client.post(f"/api/v1/agent/runs/{second_run_id}/confirm")
    assert confirm.status_code == 200
    confirmed_run = confirm.json()["run"]
    assert confirmed_run["status"] == "completed"
    assert confirmed_run["verification_status"] == "passed"
    assert (
        confirmed_run["operations"][0]["verification_summary"]
        == "预览与落库结果一致；字段验证通过：content；快照联动已校验：pre_update。"
    )
    assert confirmed_run["operations"][0]["execution_result"]["field_verification"]["matched_fields"] == ["content"]
    assert confirmed_run["operations"][0]["execution_result"]["snapshot"]["stage"] == "pre_update"
    assert confirmed_run["operations"][0]["execution_result"]["snapshot_verification"]["status"] == "passed"

    settings_response = await client.get(f"/api/v1/world-settings/project/{project_id}")
    assert settings_response.status_code == 200
    assert settings_response.json()[0]["content"] == "新设定 v2，更冷峻"


@pytest.mark.asyncio
async def test_update_character_structured_fields_are_verified(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured character updates should pass field-level verification."""
    project_id = await create_project(client, name="Character Verification")
    thread_id = await create_thread(client, project_id)

    character_response = await client.post(
        "/api/v1/characters",
        json={
            "project_id": project_id,
            "name": "林霁",
            "role": "主角",
            "profile": {"temper": "克制"},
            "notes": "旧注记",
        },
    )
    assert character_response.status_code == 201

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会先更新人物资料，再等你确认。",
                summary="更新人物 林霁",
                operations=[
                    {
                        "tool_name": "update_character",
                        "description": "补充人物资料",
                        "reason": "用户要求推进人物设定",
                        "payload": {
                            "character_name": "林霁",
                            "updates": {
                                "role": "执棋人",
                                "profile": {"temper": "冷静", "ambition": "夺权"},
                                "notes": "已补全权谋动机。",
                            },
                        },
                    }
                ],
            )
        ),
    )

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "把林霁改成更冷静的执棋人，并补上她的权谋动机"},
    )
    assert message.status_code == 200

    confirm = await client.post(f"/api/v1/agent/runs/{message.json()['run']['id']}/confirm")
    assert confirm.status_code == 200
    run = confirm.json()["run"]

    assert run["status"] == "completed"
    assert run["verification_status"] == "passed"
    assert (
        run["operations"][0]["verification_summary"]
        == "预览与落库结果一致；字段验证通过：role, profile, notes；快照联动已校验：pre_update。"
    )
    assert run["operations"][0]["execution_result"]["field_verification"]["matched_fields"] == [
        "role",
        "profile",
        "notes",
    ]
    assert run["operations"][0]["execution_result"]["field_verification"]["mismatched_fields"] == []
    assert run["operations"][0]["execution_result"]["snapshot"]["stage"] == "pre_update"
    assert run["operations"][0]["execution_result"]["snapshot_verification"]["status"] == "passed"


@pytest.mark.asyncio
async def test_update_character_profile_mismatch_fails_field_level_verification(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Structured field mismatches should fail RunStop even when summary stays unchanged."""
    project_id = await create_project(client, name="Character Verification Failure")
    thread_id = await create_thread(client, project_id)

    character_response = await client.post(
        "/api/v1/characters",
        json={
            "project_id": project_id,
            "name": "沈砚",
            "role": "谋士",
            "profile": {"temper": "平静"},
        },
    )
    assert character_response.status_code == 201

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会更新人物 profile，并先给出预览。",
                summary="更新人物 沈砚",
                operations=[
                    {
                        "tool_name": "update_character",
                        "description": "更新人物 profile",
                        "reason": "用户要求补充更强的政治野心",
                        "payload": {
                            "character_name": "沈砚",
                            "updates": {
                                "profile": {"temper": "平静", "ambition": "掌局"},
                            },
                        },
                    }
                ],
            )
        ),
    )

    async def fake_character_update(*args: object, **kwargs: object) -> object:
        return kwargs["db_obj"]

    monkeypatch.setattr(agent_workflow_module.character_service, "update", fake_character_update)

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "给沈砚补上更强的政治野心"},
    )
    assert message.status_code == 200

    confirm = await client.post(f"/api/v1/agent/runs/{message.json()['run']['id']}/confirm")
    assert confirm.status_code == 200
    run = confirm.json()["run"]

    assert run["status"] == "failed"
    assert run["verification_status"] == "failed"
    assert "字段不一致：profile" in (run["verification_summary"] or "")
    assert run["operations"][0]["verification_status"] == "failed"
    assert "字段不一致：profile" in (run["operations"][0]["verification_summary"] or "")
    assert run["meta"]["hook_trace"][-1]["hook_name"] == "RunStop"
    assert run["meta"]["hook_trace"][-1]["status"] == "failed"


@pytest.mark.asyncio
async def test_missing_snapshot_linkage_fails_verification(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RunStop should fail when the execution result references no valid persisted snapshot."""
    project_id = await create_project(client, name="Snapshot Verification Failure")
    thread_id = await create_thread(client, project_id)

    setting_response = await client.post(
        "/api/v1/world-settings",
        json={
            "project_id": project_id,
            "category": "rules",
            "name": "宫禁法度",
            "content": "旧法度",
        },
    )
    assert setting_response.status_code == 201

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会先更新法度设定，再等你确认。",
                summary="更新设定 宫禁法度",
                operations=[
                    {
                        "tool_name": "update_world_setting",
                        "description": "更新宫禁法度",
                        "reason": "用户要求补强设定",
                        "payload": {
                            "setting_name": "宫禁法度",
                            "updates": {"content": "新法度，增加了夜禁与腰牌核验。"},
                        },
                    }
                ],
            )
        ),
    )

    async def fake_create_snapshot(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            id=kwargs["target_id"],
            project_id=kwargs["project_id"],
            target_type=kwargs["target_type"],
            target_id=kwargs["target_id"],
            data=kwargs["data"],
        )

    monkeypatch.setattr(agent_workflow_module.snapshot_service, "create_snapshot", fake_create_snapshot)

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "把宫禁法度补得更完整一些"},
    )
    assert message.status_code == 200

    confirm = await client.post(f"/api/v1/agent/runs/{message.json()['run']['id']}/confirm")
    assert confirm.status_code == 200
    run = confirm.json()["run"]

    assert run["status"] == "failed"
    assert run["verification_status"] == "failed"
    assert "快照缺失" in (run["verification_summary"] or "")
    assert run["operations"][0]["verification_status"] == "failed"
    assert "快照缺失" in (run["operations"][0]["verification_summary"] or "")
    assert run["operations"][0]["execution_result"]["snapshot_verification"]["status"] == "failed"
    assert run["operations"][0]["execution_result"]["snapshot_verification"]["reason"] == "snapshot_missing"


@pytest.mark.asyncio
async def test_write_chapter_content_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The workflow can preview and write chapter content."""
    project_id = await create_project(client, name="Chapter Test")
    thread_id = await create_thread(client, project_id)

    chapter_response = await client.post(
        "/api/v1/chapters",
        json={
            "project_id": project_id,
            "chapter_number": 1,
            "title": "雨夜",
            "content": "旧正文",
        },
    )
    assert chapter_response.status_code == 201
    chapter_id = chapter_response.json()["id"]

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会重写第一章正文。",
                summary="重写第一章正文",
                warning_message="写作完成后建议手动复核记忆。",
                operations=[
                    {
                        "tool_name": "write_chapter_content",
                        "description": "改写第一章正文",
                        "reason": "用户要求重写章节",
                        "payload": {
                            "chapter_number": 1,
                            "mode": "replace",
                            "content": "雨夜压城，灯影像刀一样切过长街。",
                        },
                    }
                ],
            )
        ),
    )

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "把第一章改成更紧张的雨夜开场"},
    )
    assert message.status_code == 200
    run = message.json()["run"]
    assert run["operations"][0]["target_id"] == chapter_id

    confirm = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm.status_code == 200
    assert confirm.json()["run"]["warning_message"] is not None

    chapter = await client.get(f"/api/v1/chapters/{chapter_id}")
    assert chapter.status_code == 200
    assert chapter.json()["content"] == "雨夜压城，灯影像刀一样切过长街。"


@pytest.mark.asyncio
async def test_multi_step_run_is_transactional(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """If execution fails mid-run, earlier operations are rolled back."""
    project_id = await create_project(client, name="Txn Test")
    thread_id = await create_thread(client, project_id)

    chapter_response = await client.post(
        "/api/v1/chapters",
        json={
            "project_id": project_id,
            "chapter_number": 2,
            "title": "埋伏",
            "content": "旧内容",
        },
    )
    assert chapter_response.status_code == 201
    chapter_id = chapter_response.json()["id"]

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会创建人物并改写第二章。",
                summary="创建人物并改写第二章",
                operations=[
                    {
                        "tool_name": "create_character",
                        "description": "创建人物白隼",
                        "reason": "补充关键配角",
                        "payload": {"name": "白隼", "role": "密探"},
                    },
                    {
                        "tool_name": "write_chapter_content",
                        "description": "改写第二章",
                        "reason": "增强埋伏张力",
                        "payload": {
                            "chapter_id": chapter_id,
                            "mode": "replace",
                            "content": "新正文",
                        },
                    },
                ],
            )
        ),
    )

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建一个密探白隼，再把第二章改得更紧张"},
    )
    assert message.status_code == 200
    run = message.json()["run"]
    run_id = run["id"]
    assert run["risk_summary"]["overall_risk_level"] == "medium"
    assert run["risk_summary"]["total_operations"] == 2
    assert [policy["policy_id"] for policy in run["risk_summary"]["applied_policies"]] == ["content_rewrite"]

    delete_chapter = await client.delete(f"/api/v1/chapters/{chapter_id}")
    assert delete_chapter.status_code == 200

    confirm = await client.post(f"/api/v1/agent/runs/{run_id}/confirm")
    assert confirm.status_code == 200
    assert confirm.json()["run"]["status"] == "failed"

    characters = await client.get(f"/api/v1/characters/project/{project_id}")
    assert characters.status_code == 200
    assert characters.json() == []


@pytest.mark.asyncio
async def test_invalid_planner_tool_is_rejected(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unsupported planner tools are rejected with a client error."""
    project_id = await create_project(client, name="Invalid Tool Test")
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会直接执行黑盒工具。",
                summary="非法工具计划",
                operations=[
                    {
                        "tool_name": "delete_everything",
                        "description": "非法操作",
                        "payload": {},
                    }
                ],
            )
        ),
    )

    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "做点危险的事"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_planner_subtask_recovers_to_service_unit(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Planner-provided subtask metadata should recover to the service fallback when invalid."""
    project_id = await create_project(client, name="Recovery Test")
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会先创建人物卡。",
                summary="创建人物 周槐",
                operations=[
                    {
                        "tool_name": "create_character",
                        "description": "创建人物周槐",
                        "reason": "补充新角色",
                        "payload": {"name": "周槐", "role": "谋士"},
                    }
                ],
                subtasks=[
                    {
                        "role": "researcher",
                        "title": "Context bundle",
                        "summary": "",
                        "status": "completed",
                    }
                ],
            )
        ),
    )

    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建一个谋士周槐"},
    )
    assert response.status_code == 200
    run = response.json()["run"]

    researcher = next(subtask for subtask in run["subtasks"] if subtask["role"] == "researcher")
    assert researcher["meta"]["source"] == "service_recovery"
    assert researcher["meta"]["attempt_count"] == 2
    assert researcher["meta"]["validation_status"] == "recovered"
    assert researcher["meta"]["retry_strategy"] == "planner_then_service_fallback"
    assert researcher["child_trace"]["attempts"][0]["source"] == "planner"
    assert researcher["child_trace"]["attempts"][0]["accepted"] is False
    assert researcher["child_trace"]["attempts"][1]["source"] == "service_recovery"
    assert researcher["child_trace"]["attempts"][1]["accepted"] is True
    assert run["meta"]["hook_trace"][-1]["meta"]["recovered_roles"] == ["researcher"]
    focused_resolution = next(
        capability
        for capability in run["execution_contract"]["phases"][0]["capabilities"]
        if capability["capability_id"] == "focused_object_resolution"
    )
    assert focused_resolution["execution_record"]["status"] == "completed"


@pytest.mark.asyncio
async def test_failed_service_subtask_rejects_blueprint(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unrecoverable internal subtask failure should reject the run before persistence."""
    project_id = await create_project(client, name="Subtask Failure")
    thread_id = await create_thread(client, project_id)

    chapter_response = await client.post(
        "/api/v1/chapters",
        json={
            "project_id": project_id,
            "chapter_number": 1,
            "title": "夜潮",
            "content": "旧内容",
        },
    )
    assert chapter_response.status_code == 201

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会重写第一章。",
                summary="重写第一章正文",
                operations=[
                    {
                        "tool_name": "write_chapter_content",
                        "description": "重写第一章正文",
                        "reason": "测试 writer 单元失败",
                        "payload": {
                            "chapter_number": 1,
                            "mode": "replace",
                            "content": "新正文候选",
                        },
                    }
                ],
            )
        ),
    )
    monkeypatch.setattr(
        agent_workflow_service,
        "_execute_writer_unit",
        lambda *, operations: PlannedSubtaskSpec(
            role="writer",
            title="Writer candidate",
            status="skipped",
            summary="错误的 writer 单元",
        ),
    )

    response = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "重写第一章"},
    )
    assert response.status_code == 400
    assert "failed subtask units: writer" in response.text


@pytest.mark.asyncio
async def test_cancel_run_marks_build_capability_skipped(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelling a run should mark build capability execution as skipped."""
    project_id = await create_project(client, name="Cancel Capability")
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会先创建人物卡。",
                summary="创建人物 秦昭",
                operations=[
                    {
                        "tool_name": "create_character",
                        "description": "创建人物秦昭",
                        "reason": "测试取消链路",
                        "payload": {"name": "秦昭", "role": "刀客"},
                    }
                ],
            )
        ),
    )

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建一个刀客秦昭"},
    )
    assert message.status_code == 200
    run_id = message.json()["run"]["id"]

    cancelled = await client.post(f"/api/v1/agent/runs/{run_id}/cancel")
    assert cancelled.status_code == 200
    run = cancelled.json()["run"]
    build_phase = next(phase for phase in run["execution_contract"]["phases"] if phase["phase"] == "build")
    assert build_phase["capabilities"][0]["execution_record"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_capability_registry_endpoint(client: AsyncClient) -> None:
    """The stable capability registry should be inspectable independently from a run."""
    response = await client.get("/api/v1/agent/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["registry_version"] == "2026-03-15.1"
    capability_ids = {item["capability_id"] for item in payload["capabilities"]}
    assert {"project_inventory", "focused_object_resolution", "checkpoint_context", "operation_execution"} <= capability_ids
    operation_execution = next(item for item in payload["capabilities"] if item["capability_id"] == "operation_execution")
    assert operation_execution["policy"]["execution_phase"] == "build"
    assert operation_execution["policy"]["source_role"] == "executor"
    assert operation_execution["execution_record"] is None


@pytest.mark.asyncio
async def test_risk_policy_registry_endpoint(client: AsyncClient) -> None:
    """The stable risk policy registry should be inspectable independently from a run."""
    response = await client.get("/api/v1/agent/risk-policies")
    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_version"] == "2026-03-15.2"
    policy_ids = {item["policy_id"] for item in payload["policies"]}
    assert {
        "create_only",
        "standard_updates",
        "content_append",
        "content_rewrite",
        "long_form_overwrite",
        "multi_object_write",
    } <= policy_ids
    long_form = next(item for item in payload["policies"] if item["policy_id"] == "long_form_overwrite")
    assert long_form["confirmation_gate"] == "double"
    assert long_form["requires_secondary_confirmation"] is True
    assert "280" in long_form["description"]


@pytest.mark.asyncio
async def test_skill_catalog_endpoint(client: AsyncClient) -> None:
    """The active planner and operation skills are exposed for inspection."""
    response = await client.get("/api/v1/agent/skills")
    assert response.status_code == 200
    payload = response.json()
    assert payload["planner"]["name"] == "novel-agent-planner"
    tool_names = {item["tool_name"] for item in payload["operations"]}
    assert "create_character" in tool_names
    assert "write_chapter_content" in tool_names
    assert payload["source_roots"]


@pytest.mark.asyncio
async def test_profiles_and_project_skill_catalog(client: AsyncClient) -> None:
    """Projects can opt into a non-default profile and inspect its active skills."""
    response = await client.get("/api/v1/agent/profiles")
    assert response.status_code == 200
    profiles = {profile["id"] for profile in response.json()}
    assert "default" in profiles
    assert "xianxia_intrigue" in profiles

    project_response = await client.post(
        "/api/v1/projects",
        json={"name": "Xianxia Project", "genre": "fantasy", "agent_profile_id": "xianxia_intrigue"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    catalog_response = await client.get(f"/api/v1/agent/skills?project_id={project_id}")
    assert catalog_response.status_code == 200
    payload = catalog_response.json()
    assert payload["profile_id"] == "xianxia_intrigue"
    assert payload["planner"]["name"] == "xianxia-intrigue-planner"


@pytest.mark.asyncio
async def test_project_specific_risk_policy_registry_endpoint(client: AsyncClient) -> None:
    """Risk registry inspection should reflect the project's active profile overrides."""
    project_response = await client.post(
        "/api/v1/projects",
        json={"name": "Xianxia Risk Project", "genre": "fantasy", "agent_profile_id": "xianxia_intrigue"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    response = await client.get(f"/api/v1/agent/risk-policies?project_id={project_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_version"] == "2026-03-15.2"
    long_form = next(item for item in payload["policies"] if item["policy_id"] == "long_form_overwrite")
    assert "180" in long_form["description"]


@pytest.mark.asyncio
async def test_xianxia_profile_applies_stricter_risk_override(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The xianxia profile should promote medium-length overwrite plans to high risk."""
    project_response = await client.post(
        "/api/v1/projects",
        json={"name": "Xianxia Override", "genre": "fantasy", "agent_profile_id": "xianxia_intrigue"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    thread_id = await create_thread(client, project_id)

    chapter_response = await client.post(
        "/api/v1/chapters",
        json={
            "project_id": project_id,
            "chapter_number": 5,
            "title": "风雪关",
            "content": "旧正文",
        },
    )
    assert chapter_response.status_code == 201
    chapter_id = chapter_response.json()["id"]

    medium_content = " ".join(["夜色沉坠，皇城如渊。"] * 18)
    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会先给出重写预览，再等待你确认。",
                summary="重写第五章正文",
                operations=[
                    {
                        "tool_name": "write_chapter_content",
                        "description": "重写第五章正文",
                        "reason": "用户要求调整仙侠权谋场景节奏",
                        "payload": {
                            "chapter_id": chapter_id,
                            "mode": "replace",
                            "content": medium_content,
                        },
                    }
                ],
            )
        ),
    )

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "重写第五章，压缩成更冷峻的权谋气息"},
    )
    assert message.status_code == 200
    run = message.json()["run"]
    assert run["meta"]["profile_id"] == "xianxia_intrigue"
    assert run["operations"][0]["permission_level"] == "high_risk_write"
    assert run["operations"][0]["risk_level"] == "high"
    assert run["operations"][0]["requires_secondary_confirmation"] is True
    assert run["risk_summary"]["policy_version"] == "2026-03-15.2"
    assert run["risk_summary"]["overall_risk_level"] == "high"
    assert run["risk_summary"]["confirmation_gate"] == "double"
    assert {policy["policy_id"] for policy in run["risk_summary"]["applied_policies"]} == {
        "content_rewrite",
        "long_form_overwrite",
    }
    build_phase = next(phase for phase in run["execution_contract"]["phases"] if phase["phase"] == "build")
    assert build_phase["confirmation_gate"] == "double"
    assert build_phase["allowed_permission_levels"] == ["high_risk_write"]


@pytest.mark.asyncio
async def test_high_risk_run_requires_second_confirmation(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Large replace writes should pause for a second confirmation before execution."""
    project_id = await create_project(client, name="High Risk")
    thread_id = await create_thread(client, project_id)

    chapter_response = await client.post(
        "/api/v1/chapters",
        json={
            "project_id": project_id,
            "chapter_number": 3,
            "title": "夜行",
            "content": "旧章内容",
        },
    )
    assert chapter_response.status_code == 201
    chapter_id = chapter_response.json()["id"]

    long_content = " ".join(["夜色沉坠，皇城如渊。"] * 40)
    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会重写第三章，并先给出完整预览。",
                summary="重写第三章正文",
                operations=[
                    {
                        "tool_name": "write_chapter_content",
                        "description": "重写第三章正文",
                        "reason": "用户要求完整覆盖第三章",
                        "payload": {
                            "chapter_id": chapter_id,
                            "mode": "replace",
                            "content": long_content,
                        },
                    }
                ],
            )
        ),
    )

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "完整重写第三章，改成更冷峻的皇城夜行"},
    )
    assert message.status_code == 200
    run = message.json()["run"]
    risk_summary = run["risk_summary"]
    assert run["operations"][0]["requires_secondary_confirmation"] is True
    assert run["operations"][0]["risk_level"] == "high"
    assert risk_summary["policy_version"] == "2026-03-15.2"
    assert risk_summary["overall_risk_level"] == "high"
    assert risk_summary["confirmation_gate"] == "double"
    assert risk_summary["requires_secondary_confirmation"] is True
    assert risk_summary["high_risk_operation_positions"] == [1]
    assert risk_summary["secondary_confirmation_operation_positions"] == [1]
    assert {policy["policy_id"] for policy in risk_summary["applied_policies"]} == {
        "content_rewrite",
        "long_form_overwrite",
    }
    build_phase = next(phase for phase in run["execution_contract"]["phases"] if phase["phase"] == "build")
    assert build_phase["requires_confirmation"] is True
    assert build_phase["requires_secondary_confirmation"] is True
    assert build_phase["allowed_permission_levels"] == ["high_risk_write"]
    assert build_phase["confirmation_gate"] == "double"
    assert build_phase["capabilities"][0]["execution_record"]["status"] == "planned"
    assert [unit["role"] for unit in build_phase["child_units"]] == ["writer", "continuity", "executor"]
    assert build_phase["child_units"][0]["stage"] == "preview"
    assert build_phase["child_units"][1]["confirmation_gate"] == "double"
    assert build_phase["child_units"][2]["confirmation_gate"] == "double"

    confirm = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm")
    assert confirm.status_code == 200
    assert confirm.json()["run"]["status"] == "awaiting_high_risk_confirmation"

    confirm_high_risk = await client.post(f"/api/v1/agent/runs/{run['id']}/confirm-high-risk")
    assert confirm_high_risk.status_code == 200
    confirmed_run = confirm_high_risk.json()["run"]
    assert confirmed_run["status"] == "completed"
    assert confirmed_run["verification_status"] == "passed"
    build_phase = next(phase for phase in confirmed_run["execution_contract"]["phases"] if phase["phase"] == "build")
    assert build_phase["capabilities"][0]["execution_record"]["status"] == "completed"

    chapter = await client.get(f"/api/v1/chapters/{chapter_id}")
    assert chapter.status_code == 200
    assert chapter.json()["content"] == long_content


@pytest.mark.asyncio
async def test_multi_rewrite_batch_escalates_to_multi_object_policy(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiple rewrite operations in one run should elevate to the batch overwrite policy."""
    project_id = await create_project(client, name="Batch Rewrite")
    thread_id = await create_thread(client, project_id)

    first_chapter = await client.post(
        "/api/v1/chapters",
        json={"project_id": project_id, "chapter_number": 1, "title": "初章", "content": "旧内容一"},
    )
    assert first_chapter.status_code == 201
    second_chapter = await client.post(
        "/api/v1/chapters",
        json={"project_id": project_id, "chapter_number": 2, "title": "次章", "content": "旧内容二"},
    )
    assert second_chapter.status_code == 201

    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            return_value=planner_response(
                assistant_message="我会同时改写前两章，并先给出完整预览。",
                summary="批量改写前两章",
                operations=[
                    {
                        "tool_name": "write_chapter_content",
                        "description": "改写第一章",
                        "reason": "统一调整开场语气",
                        "payload": {
                            "chapter_id": first_chapter.json()["id"],
                            "mode": "replace",
                            "content": "新正文一",
                        },
                    },
                    {
                        "tool_name": "write_chapter_content",
                        "description": "改写第二章",
                        "reason": "统一调整推进节奏",
                        "payload": {
                            "chapter_id": second_chapter.json()["id"],
                            "mode": "replace",
                            "content": "新正文二",
                        },
                    },
                ],
            )
        ),
    )

    message = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "把前两章一起重写，风格统一一些"},
    )
    assert message.status_code == 200
    run = message.json()["run"]
    risk_summary = run["risk_summary"]
    assert run["status"] == "awaiting_confirmation"
    assert [operation["risk_level"] for operation in run["operations"]] == ["high", "high"]
    assert [operation["requires_secondary_confirmation"] for operation in run["operations"]] == [True, True]
    assert risk_summary["overall_risk_level"] == "high"
    assert risk_summary["confirmation_gate"] == "double"
    assert risk_summary["high_risk_operation_positions"] == [1, 2]
    assert risk_summary["secondary_confirmation_operation_positions"] == [1, 2]
    assert {policy["policy_id"] for policy in risk_summary["applied_policies"]} == {
        "content_rewrite",
        "multi_object_write",
    }


@pytest.mark.asyncio
async def test_thread_state_exposes_latest_checkpoint(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Thread state should surface the latest checkpoint after compaction runs."""
    project_id = await create_project(client, name="Checkpoint Test")
    thread_id = await create_thread(client, project_id)

    monkeypatch.setattr(agent_workflow_module, "COMPACTION_MESSAGE_THRESHOLD", 1)
    monkeypatch.setattr(
        agent_workflow_service.llm,
        "generate",
        AsyncMock(
            side_effect=[
                planner_response(
                    assistant_message="先创建人物。",
                    summary="创建人物",
                    operations=[
                        {
                            "tool_name": "create_character",
                            "description": "创建人物沈陵",
                            "reason": "测试压缩",
                            "payload": {"name": "沈陵", "role": "修士"},
                        }
                    ],
                ),
                planner_response(
                    assistant_message="继续创建第二个人物。",
                    summary="再次创建人物",
                    operations=[
                        {
                            "tool_name": "create_character",
                            "description": "创建人物顾照",
                            "reason": "触发 checkpoint",
                            "payload": {"name": "顾照", "role": "谋士"},
                        }
                    ],
                ),
            ]
        ),
    )

    first = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "创建一个修士人物沈陵"},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/agent/threads/{thread_id}/messages",
        json={"content": "再创建一个谋士顾照"},
    )
    assert second.status_code == 200

    state = await client.get(f"/api/v1/agent/threads/{thread_id}")
    assert state.status_code == 200
    payload = state.json()
    assert payload["latest_checkpoint"] is not None
    assert payload["latest_checkpoint"]["profile_id"] == "default"
    assert payload["latest_checkpoint"]["source_message_count"] >= 2


@pytest.mark.asyncio
async def test_legacy_chat_endpoint_still_available(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy chat remains callable for auxiliary pages."""
    project_id = await create_project(client, name="Legacy Chat")

    monkeypatch.setattr(
        "app.api.v1.agent.orchestrator.chat",
        AsyncMock(
            return_value=SimpleNamespace(
                message="legacy ok",
                suggestions=[],
                metadata={"agent_type": "draft"},
            )
        ),
    )

    response = await client.post(
        "/api/v1/agent/chat",
        json={"project_id": project_id, "message": "hello", "history": [], "context": {}},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "legacy ok"
