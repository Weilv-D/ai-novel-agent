"""Extended unit coverage for agent workflow helper logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BadRequestException
from app.models.chapter import Chapter, Scene, Volume
from app.models.character import Character
from app.models.project import Project
from app.models.world_setting import WorldSetting
from app.schemas.agent import AgentRunRiskSummaryResponse
from app.schemas.character import CharacterCreate
from app.services.agent_skill import AgentProfile, AgentSkill, AgentSkillBundle
from app.services.agent_workflow import (
    AgentWorkflowService,
    _build_diff,
    _excerpt,
    _extract_json_object,
    _hash_text,
    _json_ready,
    _serialize_model,
)


@pytest.fixture
def workflow_service() -> AgentWorkflowService:
    """Create an isolated workflow service instance for helper testing."""
    return AgentWorkflowService(llm=MagicMock())


def _make_project(project_id: uuid.UUID | None = None) -> Project:
    project = Project(
        id=project_id or uuid.uuid4(),
        name="测试项目",
        genre="Fantasy",
        summary="项目摘要",
        story_outline="项目大纲",
        notes="项目备注",
        meta={},
    )
    project.created_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    return project


class TestAgentWorkflowHelpers:
    """Covers pure helper logic and payload normalization branches."""

    def test_module_level_helpers(self) -> None:
        """JSON, diff, excerpt, hash, and planner JSON extraction helpers should behave deterministically."""
        sample_uuid = uuid.uuid4()
        sample_time = datetime.now(UTC)
        project = _make_project(sample_uuid)

        ready = _json_ready({"id": sample_uuid, "when": sample_time, "items": [sample_uuid]})
        assert ready == {
            "id": str(sample_uuid),
            "when": sample_time.isoformat(),
            "items": [str(sample_uuid)],
        }

        serialized = _serialize_model(project)
        assert serialized["id"] == str(project.id)
        assert serialized["created_at"] == project.created_at.isoformat()

        assert _excerpt(None) is None
        assert _excerpt("   ") is None
        assert _excerpt("短文本") == "短文本"
        assert _excerpt("abcdef", length=4) == "abc…"

        diff = _build_diff("第一行\n旧内容", "第一行\n新内容")
        assert diff is not None
        assert "-旧内容" in diff
        assert "+新内容" in diff
        assert _build_diff("same", "same") is None

        assert _hash_text(None) is None
        assert _hash_text("hello") is not None

        assert _extract_json_object("```json\n{\"tool\":\"create_character\"}\n```") == {"tool": "create_character"}
        assert _extract_json_object("prefix {\"ok\": true}") == {"ok": True}
        with pytest.raises(BadRequestException, match="valid JSON"):
            _extract_json_object("no json here")

    def test_character_and_world_setting_filters(self, workflow_service: AgentWorkflowService) -> None:
        """Character and world-setting payload filters should normalize and validate planner input."""
        character = workflow_service._filter_character_create_payload({"name": "  苏砚  ", "role": "主角"})
        assert character["name"] == "苏砚"
        assert character["relationships"] == {}
        assert character["arc_state"] == {}

        with pytest.raises(BadRequestException, match="requires name"):
            workflow_service._filter_character_create_payload({"name": "   "})

        assert workflow_service._filter_character_update_payload({"name": "新名", "notes": "备注", "extra": "ignored"}) == {
            "name": "新名",
            "notes": "备注",
        }
        with pytest.raises(BadRequestException, match="must be an object"):
            workflow_service._filter_character_update_payload("bad")  # type: ignore[arg-type]

        assert workflow_service._normalize_category(" Magic ") == "magic_system"
        assert workflow_service._normalize_category("unknown") == "other"

        world_setting = workflow_service._filter_world_setting_create_payload(
            {"name": "九州", "category": "Geo", "content": "山河设定"}
        )
        assert world_setting["category"] == "geography"
        assert world_setting["meta"] == {}

        assert workflow_service._filter_world_setting_update_payload({"category": "Rule", "name": "新规则"}) == {
            "category": "rules",
            "name": "新规则",
        }
        with pytest.raises(BadRequestException, match="must be an object"):
            workflow_service._filter_world_setting_update_payload("bad")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_outline_volume_chapter_and_scene_filters(self, workflow_service: AgentWorkflowService) -> None:
        """Async payload filters should derive defaults from existing project state."""
        project_id = uuid.uuid4()
        volume = Volume(id=uuid.uuid4(), project_id=project_id, volume_number=2, title="卷二", outline=None, notes=None)
        chapter = Chapter(
            id=uuid.uuid4(),
            project_id=project_id,
            volume_id=volume.id,
            chapter_number=5,
            title="第五章",
            outline=None,
            content=None,
            status="draft",
            notes=None,
        )
        scene = Scene(
            id=uuid.uuid4(),
            chapter_id=chapter.id,
            scene_order=2,
            pov_character_id=None,
            location="渡口",
            content="旧场景",
            meta={},
        )
        pov_character = Character(
            id=uuid.uuid4(),
            project_id=project_id,
            name="苏砚",
            role="主角",
            profile={},
            relationships={},
            arc_state={},
            notes=None,
        )

        with pytest.raises(BadRequestException, match="must be an object"):
            await workflow_service._filter_project_outline_update_payload("bad")  # type: ignore[arg-type]
        with pytest.raises(BadRequestException, match="non-empty story_outline"):
            await workflow_service._filter_project_outline_update_payload({"content": "   "})

        assert await workflow_service._filter_project_outline_update_payload({"content": " 新大纲 "}) == {
            "story_outline": "新大纲"
        }

        with patch("app.services.agent_workflow.volume_service.next_volume_number", new_callable=AsyncMock) as mock_next_volume:
            mock_next_volume.return_value = 3
            created_volume = await workflow_service._filter_volume_create_payload(
                MagicMock(),
                project_id=project_id,
                payload={},
            )
        assert created_volume["volume_number"] == 3
        assert created_volume["title"] == "第3卷"

        assert workflow_service._filter_volume_update_payload({"title": "卷三", "notes": "修订", "ignored": 1}) == {
            "title": "卷三",
            "notes": "修订",
        }
        with pytest.raises(BadRequestException, match="must be an object"):
            workflow_service._filter_volume_update_payload("bad")  # type: ignore[arg-type]

        with patch("app.services.agent_workflow.volume_service.get_by_project", new_callable=AsyncMock) as mock_volumes:
            with patch("app.services.agent_workflow.chapter_service.get_by_volume", new_callable=AsyncMock) as mock_chapters:
                mock_volumes.return_value = [volume]
                mock_chapters.return_value = [chapter]
                created_chapter = await workflow_service._filter_chapter_create_payload(
                    MagicMock(),
                    project_id=project_id,
                    payload={"title": "新章"},
                )
        assert created_chapter["volume_id"] == str(volume.id)
        assert created_chapter["chapter_number"] == 6
        assert created_chapter["status"] == "draft"

        assert workflow_service._filter_chapter_update_payload({"title": "修订章", "status": "writing", "ignored": 1}) == {
            "title": "修订章",
            "status": "writing",
        }
        with pytest.raises(BadRequestException, match="must be an object"):
            workflow_service._filter_chapter_update_payload("bad")  # type: ignore[arg-type]

        with patch("app.services.agent_workflow.scene_service.get_by_chapter", new_callable=AsyncMock) as mock_scenes:
            with patch.object(workflow_service, "_resolve_character", new_callable=AsyncMock) as mock_resolve_character:
                mock_scenes.return_value = [scene]
                mock_resolve_character.return_value = pov_character
                created_scene = await workflow_service._filter_scene_create_payload(
                    MagicMock(),
                    project_id=project_id,
                    chapter=chapter,
                    payload={"pov_character_name": "苏砚", "content": "新场景"},
                )
                updated_scene = await workflow_service._filter_scene_update_payload(
                    MagicMock(),
                    project_id=project_id,
                    payload={"pov_character_name": "苏砚", "location": "山门"},
                )

        assert created_scene["scene_order"] == 3
        assert created_scene["pov_character_id"] == str(pov_character.id)
        assert created_scene["chapter_id"] == str(chapter.id)
        assert updated_scene["pov_character_id"] == str(pov_character.id)
        assert "pov_character_name" not in updated_scene

        with pytest.raises(BadRequestException, match="must be an object"):
            await workflow_service._filter_scene_update_payload(MagicMock(), project_id=project_id, payload="bad")  # type: ignore[arg-type]

    def test_summary_snapshot_and_window_helpers(self, workflow_service: AgentWorkflowService) -> None:
        """Summary and snapshot helpers should produce stable, compact metadata."""
        project = _make_project()
        character = Character(
            id=uuid.uuid4(),
            project_id=project.id,
            name="苏砚",
            role="主角",
            profile={},
            relationships={},
            arc_state={},
            notes=None,
        )
        world_setting = WorldSetting(
            id=uuid.uuid4(),
            project_id=project.id,
            category="history",
            name="王朝",
            content="千年旧事",
            meta={},
        )
        volume = Volume(id=uuid.uuid4(), project_id=project.id, volume_number=1, title="卷一", outline="卷纲", notes=None)
        chapter = Chapter(
            id=uuid.uuid4(),
            project_id=project.id,
            volume_id=volume.id,
            chapter_number=1,
            title="开篇",
            outline="章纲",
            content="章节内容",
            status="draft",
            notes=None,
        )
        scene = Scene(
            id=uuid.uuid4(),
            chapter_id=chapter.id,
            scene_order=1,
            pov_character_id=character.id,
            location="山门",
            content="场景内容",
            meta={},
        )

        assert workflow_service._apply_text_mode("原文", "新增", "append") == "原文\n\n新增"
        assert workflow_service._apply_text_mode("原文", " 新文本 ", "replace") == "新文本"
        assert "苏砚 / 主角" == workflow_service._character_summary(character)
        assert "王朝 / history" in workflow_service._world_setting_summary(world_setting)
        assert "测试项目 / 项目大纲" == workflow_service._project_summary(project)
        assert "第1卷 卷一" in workflow_service._volume_summary(volume)
        assert "第1章 开篇" in workflow_service._chapter_summary(chapter)
        assert "场景 1 / 山门" in workflow_service._scene_summary(scene)

        merged = workflow_service._merge_preview_data(project, {"id": uuid.uuid4(), "summary": "新摘要"})
        assert isinstance(merged["id"], str)
        assert merged["summary"] == "新摘要"

        warning = workflow_service._execution_warning([SimpleNamespace(tool_name="write_scene_content")])
        assert warning is not None
        assert workflow_service._execution_warning([SimpleNamespace(tool_name="list_project_characters")]) is None

        bundle = AgentSkillBundle(
            profile=AgentProfile(
                id="default",
                name="Default",
                description="desc",
                builtin=True,
                root=Path("/tmp/default"),
            ),
            planner=AgentSkill(
                name="Planner",
                description="desc",
                kind="planner",
                body="body",
                source_path=Path("/tmp/planner/SKILL.md"),
            ),
            operations={
                "create_character": AgentSkill(
                    name="Create Character",
                    description="desc",
                    kind="operation",
                    body="body",
                    source_path=Path("/tmp/create-character/SKILL.md"),
                    tool_name="create_character",
                )
            },
            roots=(Path("/tmp/default"),),
        )
        snapshot = workflow_service._build_skill_snapshot(
            bundle,
            operations=[
                {"tool_name": "create_character"},
                {"tool_name": "unknown"},
            ],
        )
        assert snapshot["profile_id"] == "default"
        assert snapshot["operations"] == [
            {
                "tool_name": "create_character",
                "skill_name": "Create Character",
                "source": "/tmp/create-character/SKILL.md",
            }
        ]

        workflow_service._validate_schema(CharacterCreate, project_id=uuid.uuid4(), name="苏砚")
        with pytest.raises(BadRequestException, match="Invalid planner payload"):
            workflow_service._validate_schema(CharacterCreate, project_id=uuid.uuid4(), name="")

        compact = workflow_service._compact_policy_payload()
        assert compact["policy_version"]

        messages = [
            SimpleNamespace(id=uuid.uuid4(), content="甲", role="planner"),
            SimpleNamespace(id=uuid.uuid4(), content="乙乙", role="writer"),
            SimpleNamespace(id=uuid.uuid4(), content="乙乙", role="writer"),
        ]
        checkpoint = SimpleNamespace(id=uuid.uuid4())
        retained = workflow_service._retained_window_payload(
            history=messages,
            history_mode="recent_window",
            latest_checkpoint=checkpoint,
        )
        assert retained["message_count"] == 3
        assert retained["character_count"] == 5
        assert retained["roles"] == ["planner", "writer"]

        focused = workflow_service._focused_object_types_from_request_context(
            {"project_id": "p1", "character_id": "c1", "scene_id": "s1"}
        )
        assert focused == ["project", "character", "scene"]

    def test_response_helpers_parse_valid_and_invalid_payloads(self, workflow_service: AgentWorkflowService) -> None:
        """Response helper methods should validate stored meta and fall back safely when malformed."""
        fallback_risk = AgentRunRiskSummaryResponse(
            policy_version="2026-03-15.1",
            overall_risk_level="low",
            confirmation_gate="none",
            requires_confirmation=False,
            requires_secondary_confirmation=False,
            total_operations=0,
            low_risk_operation_count=0,
            medium_risk_operation_count=0,
            high_risk_operation_count=0,
            high_risk_operation_positions=[],
            secondary_confirmation_operation_positions=[],
            applied_policies=[],
            summary="fallback",
        )

        with patch("app.services.agent_workflow.agent_risk_service.build_run_risk_summary", return_value=fallback_risk) as mock_risk:
            risk = workflow_service._run_risk_summary_response(meta={"risk_summary": {"bad": "payload"}}, operations=[])
        assert risk == fallback_risk
        mock_risk.assert_called_once()

        valid_compact = workflow_service._compact_policy_response(
            {
                "compact_policy": {
                    "policy_version": "v1",
                    "message_threshold": 10,
                    "run_threshold": 4,
                    "char_threshold": 1000,
                    "recent_window_limit": 20,
                    "checkpoint_delta_limit": 10,
                }
            }
        )
        assert valid_compact.policy_version == "v1"
        fallback_compact = workflow_service._compact_policy_response({"compact_policy": {"policy_version": "broken"}})
        assert fallback_compact.policy_version == workflow_service._compact_policy_payload()["policy_version"]

        planner_window = workflow_service._planner_window_response(
            {
                "planner_window": {
                    "history_mode": "recent_window",
                    "history_message_count": 3,
                    "retained_message_limit": 20,
                    "checkpoint_available": True,
                }
            }
        )
        assert planner_window is not None
        assert workflow_service._planner_window_response({"planner_window": {"history_mode": "broken"}}) is None

        retained_window = workflow_service._retained_window_response(
            {
                "retained_window": {
                    "history_mode": "recent_window",
                    "message_count": 2,
                    "character_count": 8,
                    "retained_message_limit": 20,
                    "roles": ["planner"],
                }
            }
        )
        assert retained_window is not None
        assert workflow_service._retained_window_response({"retained_window": {"history_mode": "broken"}}) is None

        active_bundle = workflow_service._active_bundle_contract_response(
            {
                "active_bundle_contract": {
                    "contract_version": "v1",
                    "source": "live_context",
                    "included_sections": ["project"],
                    "focused_object_types": ["project"],
                    "includes_thread_summary": True,
                    "includes_recent_run_digest": False,
                    "collections": {
                        "characters_count": 0,
                        "characters_limit": 5,
                        "world_settings_count": 0,
                        "world_settings_limit": 5,
                        "volumes_count": 0,
                        "volumes_limit": 5,
                        "chapters_count": 0,
                        "chapters_limit": 5,
                        "current_scenes_count": 0,
                        "current_scenes_limit": 5,
                        "recent_run_digest_count": 0,
                        "recent_run_digest_limit": 5,
                    },
                }
            }
        )
        assert active_bundle is not None
        assert workflow_service._active_bundle_contract_response({"active_bundle_contract": {"source": "broken"}}) is None

        trace = workflow_service._subtask_trace_response(
            {
                "child_trace": {
                    "unit_id": "writer-1",
                    "role": "writer",
                    "execution_phase": "build_validation",
                    "retry_strategy": "service_only",
                    "depends_on": ["planner-1"],
                    "operation_positions": [1, 2],
                    "tool_scope": ["write_chapter_content"],
                    "attempts": [
                        {
                            "attempt_number": 1,
                            "source": "planner",
                            "accepted": True,
                            "validation_status": "passed",
                            "summary": "通过校验",
                        }
                    ],
                }
            }
        )
        assert trace is not None
        assert trace.unit_id == "writer-1"
        assert workflow_service._subtask_trace_response({"child_trace": {"unit_id": "broken"}}) is None

        execution_contract = workflow_service._execution_contract_response(
            {
                "permission_matrix": {
                    "registry_version": "2026-03-15.1",
                    "phases": [
                        {
                            "phase": "plan",
                            "mode": "restricted",
                            "allowed_permission_levels": ["read_search"],
                            "tool_scope": ["list_project_characters"],
                            "role_scope": ["planner"],
                            "confirmation_gate": "none",
                            "requires_confirmation": False,
                            "requires_secondary_confirmation": False,
                            "operation_count": 1,
                            "child_units": [
                                {
                                    "unit_id": "planner-1",
                                    "role": "planner",
                                    "phase": "plan",
                                    "stage": "preview",
                                    "mode": "restricted",
                                    "title": "Planner",
                                    "description": "Plan the run",
                                }
                            ],
                            "capabilities": [
                                {
                                    "capability_id": "cap-1",
                                    "name": "Project Inventory",
                                    "kind": "planning",
                                    "description": "Load project state",
                                    "tool_scope": ["list_project_characters"],
                                    "policy": {
                                        "execution_phase": "plan",
                                        "source_role": "planner",
                                        "confirmation_gate": "none",
                                    },
                                }
                            ],
                        }
                    ],
                }
            }
        )
        assert execution_contract is not None
        assert execution_contract.registry_version == "2026-03-15.1"
        assert workflow_service._execution_contract_response({"permission_matrix": {"phases": "broken"}}) is None

        checkpoint = SimpleNamespace(
            id=uuid.uuid4(),
            thread_id=uuid.uuid4(),
            profile_id="default",
            thread_summary="summary",
            active_object_bundle={
                "compact_policy": {
                    "policy_version": "v1",
                    "message_threshold": 10,
                    "run_threshold": 4,
                    "char_threshold": 1000,
                    "recent_window_limit": 20,
                    "checkpoint_delta_limit": 10,
                },
                "compaction_boundary": {
                    "history_mode": "recent_window",
                    "source_message_count": 3,
                    "source_run_count": 1,
                },
                "active_bundle_contract": {
                    "contract_version": "v1",
                    "source": "checkpoint_plus_live_context",
                    "included_sections": ["project"],
                    "focused_object_types": ["project"],
                    "includes_thread_summary": True,
                    "includes_recent_run_digest": False,
                    "collections": {
                        "characters_count": 0,
                        "characters_limit": 5,
                        "world_settings_count": 0,
                        "world_settings_limit": 5,
                        "volumes_count": 0,
                        "volumes_limit": 5,
                        "chapters_count": 0,
                        "chapters_limit": 5,
                        "current_scenes_count": 0,
                        "current_scenes_limit": 5,
                        "recent_run_digest_count": 0,
                        "recent_run_digest_limit": 5,
                    },
                },
            },
            recent_run_digest={},
            source_message_count=3,
            source_run_count=1,
            total_context_characters=120,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        checkpoint_response = workflow_service._checkpoint_response(checkpoint)
        assert checkpoint_response.active_bundle_contract is not None
        assert checkpoint_response.active_bundle_contract.checkpoint_id == checkpoint.id
