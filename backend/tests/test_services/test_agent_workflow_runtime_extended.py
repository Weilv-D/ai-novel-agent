"""Additional unit coverage for runtime-oriented AgentWorkflowService paths."""

from __future__ import annotations

import json
import uuid
from contextlib import ExitStack
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.agent_workflow import AgentOperationStatus, AgentRunStatus, AgentVerificationStatus
from app.models.chapter import Chapter, Scene, Volume
from app.models.character import Character
from app.models.project import Project
from app.models.world_setting import WorldSetting
from app.schemas.agent import AgentRunRiskSummaryResponse
from app.services.agent_workflow import (
    AgentWorkflowService,
    HookTraceEntry,
    PlannedOperationSpec,
    PlannerOutput,
)


class FakeScalarResult:
    """SQLAlchemy-like scalar result stub."""

    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


@pytest.fixture
def workflow_service() -> AgentWorkflowService:
    """Create a workflow service with a mocked LLM backend."""
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
    project.agent_profile_id = "default"
    project.created_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    return project


def _make_run(status: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=status,
        meta={},
        warning_message=None,
        confirmed_at=None,
        secondary_confirmed_at=None,
        completed_at=None,
        verification_status=None,
        verification_summary=None,
    )


class TestProjectContextLoading:
    """Covers focused context assembly branches for runs."""

    @pytest.mark.asyncio
    async def test_load_project_context_includes_checkpoint_and_explicit_focus(self, workflow_service: AgentWorkflowService) -> None:
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
        setting = WorldSetting(
            id=uuid.uuid4(),
            project_id=project.id,
            category="rules",
            name="禁术",
            content="不可越级施法",
            meta={},
        )
        volume = Volume(
            id=uuid.uuid4(),
            project_id=project.id,
            volume_number=1,
            title="卷一",
            outline="卷纲",
            notes="卷注",
        )
        chapter = Chapter(
            id=uuid.uuid4(),
            project_id=project.id,
            volume_id=volume.id,
            chapter_number=2,
            title="夜探",
            outline="章纲",
            content="A" * 500,
            status="draft",
            notes=None,
        )
        scene = Scene(
            id=uuid.uuid4(),
            chapter_id=chapter.id,
            scene_order=3,
            pov_character_id=character.id,
            location="山门",
            content="B" * 500,
            meta={},
        )
        checkpoint = SimpleNamespace(
            id=uuid.uuid4(),
            profile_id="default",
            thread_summary="thread summary",
            active_object_bundle={"foo": "bar"},
            recent_run_digest={"runs": 1},
        )

        with patch("app.services.context_assembler.character_service.get_by_project", new_callable=AsyncMock) as mock_chars:
            with patch("app.services.context_assembler.world_setting_service.get_by_project", new_callable=AsyncMock) as mock_settings:
                with patch("app.services.context_assembler.volume_service.get_by_project", new_callable=AsyncMock) as mock_volumes:
                    with patch("app.services.context_assembler.chapter_service.get_by_project", new_callable=AsyncMock) as mock_chapters:
                        with patch("app.services.context_assembler.volume_service.get", new_callable=AsyncMock) as mock_get_volume:
                                with patch("app.services.context_assembler.chapter_service.get_by_volume", new_callable=AsyncMock) as mock_volume_chapters:
                                    with patch("app.services.context_assembler.scene_service.get", new_callable=AsyncMock) as mock_get_scene:
                                        with patch("app.services.context_assembler.scene_service.get_by_chapter", new_callable=AsyncMock) as mock_scenes:
                                            with patch("app.services.context_assembler.character_service.get", new_callable=AsyncMock) as mock_get_character:
                                                mock_chars.return_value = [character]
                                                mock_settings.return_value = [setting]
                                                mock_volumes.return_value = [volume]
                                                mock_chapters.return_value = [chapter]
                                                mock_get_volume.return_value = volume
                                                mock_volume_chapters.return_value = [chapter]
                                                mock_get_scene.return_value = scene
                                                mock_scenes.return_value = [scene]
                                                mock_get_character.return_value = character

                                                context = await workflow_service._load_project_context(
                                                    MagicMock(),
                                                    project=project,
                                                    request_context={
                                                        "volume_id": str(volume.id),
                                                        "scene_id": str(scene.id),
                                                        "character_id": str(character.id),
                                                    },
                                                    latest_checkpoint=checkpoint,
                                                )

        assert context["agent_profile_id"] == "default"
        assert context["latest_checkpoint"]["id"] == str(checkpoint.id)
        assert context["current_volume"]["id"] == str(volume.id)
        assert context["current_volume_chapters"][0]["chapter_number"] == 2
        assert context["current_scene"]["content"].endswith("…")
        assert context["current_character"]["name"] == "苏砚"

    @pytest.mark.asyncio
    async def test_load_project_context_falls_back_from_chapter_and_ignores_failed_focus_lookups(
        self,
        workflow_service: AgentWorkflowService,
    ) -> None:
        project = _make_project()
        volume = Volume(
            id=uuid.uuid4(),
            project_id=project.id,
            volume_number=1,
            title="卷一",
            outline="卷纲",
            notes=None,
        )
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
            pov_character_id=None,
            location="古道",
            content="场景内容",
            meta={},
        )

        with patch("app.services.context_assembler.character_service.get_by_project", new_callable=AsyncMock) as mock_chars:
            with patch("app.services.context_assembler.world_setting_service.get_by_project", new_callable=AsyncMock) as mock_settings:
                with patch("app.services.context_assembler.volume_service.get_by_project", new_callable=AsyncMock) as mock_volumes:
                    with patch("app.services.context_assembler.chapter_service.get_by_project", new_callable=AsyncMock) as mock_chapters:
                        with patch("app.services.context_assembler.volume_service.get", new_callable=AsyncMock) as mock_get_volume:
                            with patch("app.services.context_assembler.chapter_service.get", new_callable=AsyncMock) as mock_get_chapter:
                                with patch("app.services.context_assembler.chapter_service.get_by_volume", new_callable=AsyncMock) as mock_volume_chapters:
                                    with patch("app.services.context_assembler.scene_service.get_by_chapter", new_callable=AsyncMock) as mock_scenes:
                                        with patch("app.services.context_assembler.scene_service.get", new_callable=AsyncMock) as mock_get_scene:
                                            with patch("app.services.context_assembler.character_service.get", new_callable=AsyncMock) as mock_get_character:
                                                mock_chars.return_value = []
                                                mock_settings.return_value = []
                                                mock_volumes.return_value = [volume]
                                                mock_chapters.return_value = [chapter]
                                                mock_get_volume.side_effect = [RuntimeError("missing explicit volume"), volume]
                                                mock_get_chapter.return_value = chapter
                                                mock_volume_chapters.return_value = [chapter]
                                                mock_scenes.return_value = [scene]
                                                mock_get_scene.side_effect = RuntimeError("missing scene")
                                                mock_get_character.side_effect = RuntimeError("missing character")

                                                context = await workflow_service._load_project_context(
                                                    MagicMock(),
                                                    project=project,
                                                    request_context={
                                                        "volume_id": str(uuid.uuid4()),
                                                        "chapter_id": str(chapter.id),
                                                        "scene_id": str(uuid.uuid4()),
                                                        "character_id": str(uuid.uuid4()),
                                                    },
                                                )

        assert context["current_chapter"]["id"] == str(chapter.id)
        assert context["current_scenes"][0]["scene_order"] == 1
        assert context["current_volume"]["id"] == str(volume.id)
        assert "current_scene" not in context
        assert "current_character" not in context


class TestPlannerAndFixtureHelpers:
    """Covers planner history selection and fixture-based planning."""

    @pytest.mark.asyncio
    async def test_planner_history_switches_between_recent_window_and_checkpoint_delta(
        self,
        workflow_service: AgentWorkflowService,
    ) -> None:
        current_user_id = uuid.uuid4()
        old_message = SimpleNamespace(id=uuid.uuid4())
        current_message = SimpleNamespace(id=current_user_id)
        checkpoint = SimpleNamespace(source_message_count=9)

        with patch.object(workflow_service.message_store, "list_recent_history", new_callable=AsyncMock) as mock_recent:
            with patch.object(workflow_service.message_store, "list_after_offset", new_callable=AsyncMock) as mock_after:
                mock_recent.return_value = [old_message, current_message]
                mock_after.return_value = [current_message, old_message]

                recent_history, recent_mode = await workflow_service._planner_history(
                    MagicMock(),
                    thread_id=uuid.uuid4(),
                    latest_checkpoint=None,
                    current_user_message_id=current_user_id,
                )
                checkpoint_history, checkpoint_mode = await workflow_service._planner_history(
                    MagicMock(),
                    thread_id=uuid.uuid4(),
                    latest_checkpoint=checkpoint,
                    current_user_message_id=current_user_id,
                )

        assert recent_mode == "recent_window"
        assert recent_history == [old_message]
        assert checkpoint_mode == "checkpoint_delta"
        assert checkpoint_history == [old_message]

    @pytest.mark.asyncio
    async def test_plan_with_fixture_validates_fixture_configuration(self, workflow_service: AgentWorkflowService, tmp_path) -> None:
        with patch("app.core.config.get_settings", return_value=SimpleNamespace(agent_e2e_fixture_path="")):
            with pytest.raises(BadRequestException, match="not configured"):
                await workflow_service._plan_with_fixture(user_message="创建人物")

        fixture_root = tmp_path / "fixtures"
        fixture_root.mkdir()

        with patch("app.core.config.get_settings", return_value=SimpleNamespace(agent_e2e_fixture_path=str(fixture_root))):
            with pytest.raises(BadRequestException, match="Fixture file not found"):
                await workflow_service._plan_with_fixture(user_message="创建人物")

        fixture_file = fixture_root / "planner-responses.json"
        fixture_file.write_text(json.dumps({"其他消息": {"assistant_message": "hi", "operations": []}}, ensure_ascii=False), encoding="utf-8")
        with patch("app.core.config.get_settings", return_value=SimpleNamespace(agent_e2e_fixture_path=str(fixture_root))):
            with pytest.raises(BadRequestException, match="No fixture found for message"):
                await workflow_service._plan_with_fixture(user_message=" 创建人物 ")

        fixture_file.write_text(json.dumps({"创建人物": {"assistant_message": ""}}, ensure_ascii=False), encoding="utf-8")
        with patch("app.core.config.get_settings", return_value=SimpleNamespace(agent_e2e_fixture_path=str(fixture_root))):
            with pytest.raises(BadRequestException, match="Invalid fixture response"):
                await workflow_service._plan_with_fixture(user_message="创建人物")

        fixture_file.write_text(
            json.dumps(
                {
                    "创建人物": {
                        "assistant_message": "创建中",
                        "operations": [{"tool_name": "not_supported", "description": "bad", "payload": {}}],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        with patch("app.core.config.get_settings", return_value=SimpleNamespace(agent_e2e_fixture_path=str(fixture_root))):
            with pytest.raises(BadRequestException, match="unsupported tool"):
                await workflow_service._plan_with_fixture(user_message="创建人物")

    @pytest.mark.asyncio
    async def test_plan_with_fixture_returns_valid_planner_output(self, workflow_service: AgentWorkflowService, tmp_path) -> None:
        fixture_root = tmp_path / "fixtures"
        fixture_root.mkdir()
        (fixture_root / "planner-responses.json").write_text(
            json.dumps(
                {
                    "创建人物": {
                        "assistant_message": "好的，开始创建。",
                        "summary": "创建新角色",
                        "operations": [
                            {
                                "tool_name": "create_character",
                                "description": "创建人物",
                                "payload": {"name": "苏砚"},
                            }
                        ],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with patch("app.core.config.get_settings", return_value=SimpleNamespace(agent_e2e_fixture_path=str(fixture_root))):
            planner_output = await workflow_service._plan_with_fixture(user_message=" 创建人物 ")

        assert planner_output.assistant_message == "好的，开始创建。"
        assert planner_output.operations[0].tool_name == "create_character"

    @pytest.mark.asyncio
    async def test_stream_planned_run_emits_status_progress_and_result(self, workflow_service: AgentWorkflowService) -> None:
        project = _make_project()
        thread = SimpleNamespace(id=uuid.uuid4(), project_id=project.id)
        checkpoint = SimpleNamespace(id=uuid.uuid4())
        user_message = SimpleNamespace(id=uuid.uuid4())
        assistant_message = SimpleNamespace(id=uuid.uuid4())
        run = SimpleNamespace(id=uuid.uuid4())
        planner_output = PlannerOutput(
            assistant_message="好的，开始规划。",
            summary="创建角色",
            operations=[
                PlannedOperationSpec(
                    tool_name="create_character",
                    description="创建人物",
                    payload={"name": "苏砚"},
                )
            ],
        )
        risk_summary = AgentRunRiskSummaryResponse(
            policy_version="2026-03-15.1",
            overall_risk_level="low",
            confirmation_gate="none",
            requires_confirmation=False,
            requires_secondary_confirmation=False,
            total_operations=1,
            low_risk_operation_count=1,
            medium_risk_operation_count=0,
            high_risk_operation_count=0,
            high_risk_operation_positions=[],
            secondary_confirmation_operation_positions=[],
            applied_policies=[],
            summary="low risk",
        )

        def _dumpable(payload: dict[str, object]) -> SimpleNamespace:
            return SimpleNamespace(model_dump=lambda mode="json": payload)

        with ExitStack() as stack:
            mock_get_thread = stack.enter_context(patch.object(workflow_service.thread_store, "get", new_callable=AsyncMock))
            mock_get_project = stack.enter_context(patch("app.services.agent_workflow.project_service.get", new_callable=AsyncMock))
            mock_pending_run = stack.enter_context(patch.object(workflow_service.run_store, "get_latest_pending", new_callable=AsyncMock))
            mock_messages = stack.enter_context(patch.object(workflow_service.message_store, "list_by_thread", new_callable=AsyncMock))
            mock_recent_runs = stack.enter_context(patch.object(workflow_service.run_store, "list_recent_by_thread", new_callable=AsyncMock))
            mock_load_bundle = stack.enter_context(patch("app.services.agent_workflow.agent_skill_service.load_bundle"))
            mock_create_message = stack.enter_context(patch.object(workflow_service.message_store, "create", new_callable=AsyncMock))
            mock_compact = stack.enter_context(patch.object(workflow_service, "_maybe_compact_thread", new_callable=AsyncMock))
            mock_history = stack.enter_context(patch.object(workflow_service, "_planner_history", new_callable=AsyncMock))
            mock_context = stack.enter_context(patch.object(workflow_service, "_load_project_context", new_callable=AsyncMock))
            mock_retained = stack.enter_context(patch.object(workflow_service, "_retained_window_payload"))
            mock_bundle_contract = stack.enter_context(patch.object(workflow_service, "_active_bundle_contract_payload_for_run"))
            mock_preplan_hook = stack.enter_context(patch.object(workflow_service, "_build_pre_plan_hook"))
            mock_plan = stack.enter_context(patch.object(workflow_service, "_plan_with_llm", new_callable=AsyncMock))
            mock_prepare_ops = stack.enter_context(patch.object(workflow_service, "_prepare_operations", new_callable=AsyncMock))
            mock_classify_ops = stack.enter_context(patch.object(workflow_service, "_classify_operations"))
            mock_risk = stack.enter_context(patch("app.services.agent_workflow.agent_risk_service.build_run_risk_summary"))
            mock_subtasks = stack.enter_context(patch.object(workflow_service, "_build_subtasks"))
            mock_contract = stack.enter_context(patch.object(workflow_service, "_build_execution_contract_payload"))
            mock_blueprint = stack.enter_context(patch.object(workflow_service, "_validate_blueprint"))
            mock_create_run = stack.enter_context(patch.object(workflow_service.run_store, "create", new_callable=AsyncMock))
            mock_create_ops = stack.enter_context(patch.object(workflow_service.operation_store, "create_many", new_callable=AsyncMock))
            mock_create_subtasks = stack.enter_context(patch.object(workflow_service.subtask_store, "create_many", new_callable=AsyncMock))
            mock_supersede = stack.enter_context(patch.object(workflow_service.run_store, "supersede_pending_runs", new_callable=AsyncMock))
            mock_snapshot = stack.enter_context(patch.object(workflow_service, "_build_skill_snapshot"))
            mock_thread_response = stack.enter_context(patch.object(workflow_service, "_thread_response"))
            mock_message_response = stack.enter_context(patch.object(workflow_service, "_message_response"))
            mock_run_response = stack.enter_context(patch.object(workflow_service, "_run_response", new_callable=AsyncMock))

            mock_get_thread.return_value = thread
            mock_get_project.return_value = project
            mock_pending_run.return_value = None
            mock_messages.return_value = []
            mock_recent_runs.return_value = []
            mock_load_bundle.return_value = SimpleNamespace()
            mock_create_message.side_effect = [user_message, assistant_message]
            mock_compact.return_value = (
                checkpoint,
                HookTraceEntry(hook_name="PreCompact", status="completed"),
            )
            mock_history.return_value = ([SimpleNamespace(id=uuid.uuid4())], "recent_window")
            mock_context.return_value = {"project": {"id": str(project.id)}}
            mock_retained.return_value = {"message_count": 1}
            mock_bundle_contract.return_value = {"source": "live_context"}
            mock_preplan_hook.return_value = HookTraceEntry(hook_name="PrePlan", status="completed")
            mock_plan.return_value = planner_output
            mock_prepare_ops.return_value = [{"tool_name": "create_character", "description": "创建人物"}]
            mock_classify_ops.return_value = [{"tool_name": "create_character", "description": "创建人物"}]
            mock_risk.return_value = risk_summary
            mock_subtasks.return_value = [{"role": "writer"}]
            mock_contract.return_value = {"registry_version": "2026-03-15.1"}
            mock_blueprint.return_value = HookTraceEntry(hook_name="SubagentStop", status="completed")
            mock_create_run.return_value = run
            mock_snapshot.return_value = {"profile_id": "default"}
            mock_thread_response.return_value = _dumpable({"id": str(thread.id)})
            mock_message_response.side_effect = [
                _dumpable({"id": str(user_message.id)}),
                _dumpable({"id": str(assistant_message.id)}),
            ]
            mock_run_response.return_value = _dumpable({"id": str(run.id)})

            events = [
                event
                async for event in workflow_service.stream_planned_run(
                    MagicMock(),
                    thread_id=thread.id,
                    content="创建角色",
                )
            ]

        assert [event.stage for event in events[:4]] == ["init", "load_context", "compact_check", "planning"]
        assert any(event.type == "operation_progress" for event in events)
        assert events[-1].type == "result"
        assert events[-1].detail["run"]["id"] == str(run.id)
        mock_create_ops.assert_awaited_once()
        mock_create_subtasks.assert_awaited_once()
        mock_supersede.assert_awaited_once()


class TestRunStateTransitions:
    """Covers cancel/confirm/high-risk confirmation branches."""

    @pytest.mark.asyncio
    async def test_cancel_run_response_marks_run_and_operations_cancelled(self, workflow_service: AgentWorkflowService) -> None:
        run = _make_run(AgentRunStatus.AWAITING_CONFIRMATION.value)
        operations = [
            SimpleNamespace(status="draft", verification_status="pending", verification_summary=None),
            SimpleNamespace(status="draft", verification_status="pending", verification_summary=None),
        ]
        db = MagicMock()
        db.flush = AsyncMock()

        with patch.object(workflow_service.run_store, "get", new_callable=AsyncMock) as mock_get_run:
            with patch.object(workflow_service.operation_store, "list_by_run", new_callable=AsyncMock) as mock_list_operations:
                with patch.object(workflow_service, "_run_response", new_callable=AsyncMock) as mock_run_response:
                    with patch("app.services.agent_workflow.AgentRunActionResponse", side_effect=lambda **kwargs: SimpleNamespace(**kwargs)):
                        mock_get_run.return_value = run
                        mock_list_operations.return_value = operations
                        mock_run_response.return_value = {"id": str(run.id)}

                        response = await workflow_service.cancel_run_response(db, run_id=run.id)

        assert run.status == AgentRunStatus.CANCELLED.value
        assert run.verification_status == AgentVerificationStatus.SKIPPED.value
        assert all(operation.status == AgentOperationStatus.CANCELLED.value for operation in operations)
        assert response.run == {"id": str(run.id)}
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_run_response_rejects_completed_runs(self, workflow_service: AgentWorkflowService) -> None:
        run = _make_run(AgentRunStatus.COMPLETED.value)
        with patch.object(workflow_service.run_store, "get", new_callable=AsyncMock) as mock_get_run:
            mock_get_run.return_value = run
            with pytest.raises(BadRequestException, match="can be cancelled"):
                await workflow_service.cancel_run_response(MagicMock(), run_id=run.id)

    @pytest.mark.asyncio
    async def test_confirm_run_response_handles_high_risk_gate_and_execute_path(self, workflow_service: AgentWorkflowService) -> None:
        run = _make_run(AgentRunStatus.AWAITING_CONFIRMATION.value)
        low_risk_run = _make_run(AgentRunStatus.AWAITING_CONFIRMATION.value)
        high_risk_operation = SimpleNamespace(requires_secondary_confirmation=True)
        low_risk_operation = SimpleNamespace(requires_secondary_confirmation=False)
        db = MagicMock()
        db.flush = AsyncMock()

        with patch.object(workflow_service.run_store, "get", new_callable=AsyncMock) as mock_get_run:
            with patch.object(workflow_service.operation_store, "list_by_run", new_callable=AsyncMock) as mock_list_operations:
                with patch.object(workflow_service, "_run_response", new_callable=AsyncMock) as mock_run_response:
                    with patch.object(workflow_service, "_execute_run", new_callable=AsyncMock) as mock_execute_run:
                        with patch("app.services.agent_workflow.AgentRunActionResponse", side_effect=lambda **kwargs: SimpleNamespace(**kwargs)):
                            mock_get_run.side_effect = [run, low_risk_run]
                            mock_list_operations.return_value = [high_risk_operation]
                            mock_run_response.return_value = {"status": AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value}

                            gated = await workflow_service.confirm_run_response(db, run_id=run.id)
                            mock_list_operations.return_value = [low_risk_operation]
                            mock_execute_run.return_value = "executed"
                            executed = await workflow_service.confirm_run_response(db, run_id=run.id)

        assert run.status == AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value
        assert gated.run == {"status": AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value}
        assert executed == "executed"

    @pytest.mark.asyncio
    async def test_confirm_high_risk_run_response_validates_status(self, workflow_service: AgentWorkflowService) -> None:
        run = _make_run(AgentRunStatus.AWAITING_HIGH_RISK_CONFIRMATION.value)
        operation = SimpleNamespace()

        with patch.object(workflow_service.run_store, "get", new_callable=AsyncMock) as mock_get_run:
            with patch.object(workflow_service.operation_store, "list_by_run", new_callable=AsyncMock) as mock_list_operations:
                with patch.object(workflow_service, "_execute_run", new_callable=AsyncMock) as mock_execute_run:
                    mock_get_run.return_value = run
                    mock_list_operations.return_value = [operation]
                    mock_execute_run.return_value = "executed"

                    assert await workflow_service.confirm_high_risk_run_response(MagicMock(), run_id=run.id) == "executed"

                    run.status = AgentRunStatus.COMPLETED.value
                    with pytest.raises(BadRequestException, match="high-risk confirmation"):
                        await workflow_service.confirm_high_risk_run_response(MagicMock(), run_id=run.id)


class TestTargetResolution:
    """Covers target resolution helpers for planner operations."""

    @pytest.mark.asyncio
    async def test_resolve_character_world_setting_and_project_paths(self, workflow_service: AgentWorkflowService) -> None:
        project_id = uuid.uuid4()
        character = Character(
            id=uuid.uuid4(),
            project_id=project_id,
            name="苏砚",
            role="主角",
            profile={},
            relationships={},
            arc_state={},
            notes=None,
        )
        setting = WorldSetting(
            id=uuid.uuid4(),
            project_id=project_id,
            category="rules",
            name="禁术",
            content="不可越级施法",
            meta={},
        )
        project = _make_project(project_id)

        with patch("app.services.agent_workflow.character_service.get", new_callable=AsyncMock) as mock_get_character:
            with patch("app.services.agent_workflow.world_setting_service.get", new_callable=AsyncMock) as mock_get_setting:
                with patch("app.services.agent_workflow.project_service.get", new_callable=AsyncMock) as mock_get_project:
                    mock_get_character.return_value = character
                    mock_get_setting.return_value = setting
                    mock_get_project.return_value = project

                    assert await workflow_service._resolve_character(
                        MagicMock(),
                        project_id=project_id,
                        payload={"character_id": str(character.id)},
                        request_context={},
                    ) is character
                    assert await workflow_service._resolve_world_setting(
                        MagicMock(),
                        project_id=project_id,
                        payload={},
                        request_context={"setting_id": str(setting.id)},
                    ) is setting
                    assert await workflow_service._resolve_project(
                        MagicMock(),
                        project_id=project_id,
                        payload={},
                        request_context={},
                    ) is project

                    other_project = _make_project()
                    mock_get_project.return_value = other_project
                    with pytest.raises(NotFoundException, match="active workspace"):
                        await workflow_service._resolve_project(
                            MagicMock(),
                            project_id=project_id,
                            payload={},
                            request_context={"project_id": str(other_project.id)},
                        )

    @pytest.mark.asyncio
    async def test_resolve_name_number_and_scene_order_fallbacks(self, workflow_service: AgentWorkflowService) -> None:
        project_id = uuid.uuid4()
        volume = Volume(
            id=uuid.uuid4(),
            project_id=project_id,
            volume_number=2,
            title="卷二",
            outline=None,
            notes=None,
        )
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
            scene_order=4,
            pov_character_id=None,
            location="渡口",
            content="场景内容",
            meta={},
        )
        character = Character(
            id=uuid.uuid4(),
            project_id=project_id,
            name="苏砚",
            role="主角",
            profile={},
            relationships={},
            arc_state={},
            notes=None,
        )
        setting = WorldSetting(
            id=uuid.uuid4(),
            project_id=project_id,
            category="rules",
            name="禁术",
            content="不可越级施法",
            meta={},
        )
        db = MagicMock()
        db.execute = AsyncMock(
            side_effect=[
                FakeScalarResult(character),
                FakeScalarResult(setting),
                FakeScalarResult(volume),
                FakeScalarResult(scene),
                FakeScalarResult(None),
            ]
        )

        with patch("app.services.agent_workflow.volume_service.get_by_volume_number", new_callable=AsyncMock) as mock_get_by_number:
            with patch.object(workflow_service, "_resolve_chapter", new_callable=AsyncMock) as mock_resolve_chapter:
                mock_get_by_number.return_value = None
                mock_resolve_chapter.return_value = chapter

                assert await workflow_service._resolve_character(
                    db,
                    project_id=project_id,
                    payload={"character_name": "苏砚"},
                    request_context={},
                ) is character
                assert await workflow_service._resolve_world_setting(
                    db,
                    project_id=project_id,
                    payload={},
                    request_context={"setting_name": "禁术"},
                ) is setting
                assert await workflow_service._resolve_volume(
                    db,
                    project_id=project_id,
                    payload={"title": "卷二"},
                    request_context={},
                ) is volume
                assert await workflow_service._resolve_chapter(
                    db,
                    project_id=project_id,
                    payload={},
                    request_context={"chapter_number": 5},
                ) is chapter
                assert await workflow_service._resolve_scene(
                    db,
                    project_id=project_id,
                    payload={"scene_order": 4},
                    request_context={},
                ) is scene
                with pytest.raises(NotFoundException, match="could not be resolved"):
                    await workflow_service._resolve_scene(
                        db,
                        project_id=project_id,
                        payload={"scene_order": 99},
                        request_context={},
                    )
