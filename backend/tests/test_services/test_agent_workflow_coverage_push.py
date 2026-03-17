"""Focused coverage expansion for AgentWorkflowService high-miss branches."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.agent_workflow import AgentSubtaskStatus, AgentVerificationStatus
from app.models.chapter import Chapter, Scene, Volume
from app.models.character import Character
from app.models.project import Project
from app.models.world_setting import WorldSetting
from app.services.agent_workflow import AgentWorkflowService, PlannedOperationSpec


class FakeScalarResult:
    """Small scalar result stub used for duplicate-check queries."""

    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


@pytest.fixture
def workflow_service() -> AgentWorkflowService:
    """Create a workflow service with mocked LLM dependencies."""
    return AgentWorkflowService(llm=MagicMock())


def _make_project(project_id: uuid.UUID | None = None, *, story_outline: str | None = "项目大纲") -> Project:
    project = Project(
        id=project_id or uuid.uuid4(),
        name="山海夜行",
        genre="fantasy",
        summary="项目摘要",
        story_outline=story_outline,
        notes="项目备注",
        meta={},
    )
    project.agent_profile_id = "default"
    project.created_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    return project


def _make_volume(project_id: uuid.UUID, *, volume_number: int = 1, title: str = "卷一") -> Volume:
    volume = Volume(
        id=uuid.uuid4(),
        project_id=project_id,
        volume_number=volume_number,
        title=title,
        outline="卷纲",
        notes="卷备注",
    )
    volume.created_at = datetime.now(UTC)
    volume.updated_at = datetime.now(UTC)
    return volume


def _make_chapter(project_id: uuid.UUID, volume_id: uuid.UUID | None, *, chapter_number: int = 1, title: str = "第一章", content: str | None = "旧正文") -> Chapter:
    chapter = Chapter(
        id=uuid.uuid4(),
        project_id=project_id,
        volume_id=volume_id,
        chapter_number=chapter_number,
        title=title,
        outline="章纲",
        content=content,
        status="draft",
        notes="章备注",
    )
    chapter.created_at = datetime.now(UTC)
    chapter.updated_at = datetime.now(UTC)
    return chapter


def _make_scene(chapter_id: uuid.UUID, *, scene_order: int = 1, content: str | None = "旧场景", pov_character_id: uuid.UUID | None = None) -> Scene:
    scene = Scene(
        id=uuid.uuid4(),
        chapter_id=chapter_id,
        scene_order=scene_order,
        pov_character_id=pov_character_id,
        location="山门",
        content=content,
        meta={},
    )
    scene.created_at = datetime.now(UTC)
    scene.updated_at = datetime.now(UTC)
    return scene


def _make_character(project_id: uuid.UUID, *, name: str = "苏砚", role: str = "主角", age: object | None = None) -> Character:
    profile = {}
    if age is not None:
        profile["age"] = age
    character = Character(
        id=uuid.uuid4(),
        project_id=project_id,
        name=name,
        role=role,
        profile=profile,
        relationships={},
        arc_state={},
        notes="人物备注",
    )
    character.created_at = datetime.now(UTC)
    character.updated_at = datetime.now(UTC)
    return character


def _make_setting(project_id: uuid.UUID, *, category: str = "rules", name: str = "禁术", content: str = "不可越级施法") -> WorldSetting:
    setting = WorldSetting(
        id=uuid.uuid4(),
        project_id=project_id,
        category=category,
        name=name,
        content=content,
        meta={},
    )
    setting.created_at = datetime.now(UTC)
    setting.updated_at = datetime.now(UTC)
    return setting


def _planned(tool_name: str, payload: dict[str, object], *, description: str = "执行") -> PlannedOperationSpec:
    return PlannedOperationSpec(tool_name=tool_name, description=description, payload=payload)


def _operation(tool_name: str, payload: dict[str, object], *, target_id: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        tool_name=tool_name,
        description=f"{tool_name} description",
        payload=payload,
        preview={},
        execution_result=None,
        target_id=target_id,
        target_type=None,
        target_display=None,
        status="planned",
        verification_status=AgentVerificationStatus.PENDING.value,
        verification_summary=None,
    )


class TestCompactionBranches:
    """Covers skipped/reused/created checkpoint branches."""

    @pytest.mark.asyncio
    async def test_maybe_compact_thread_skips_when_threshold_not_reached(self, workflow_service: AgentWorkflowService) -> None:
        thread = SimpleNamespace(id=uuid.uuid4())
        project = _make_project()
        history = [SimpleNamespace(content="短消息")]

        with patch.object(workflow_service.checkpoint_store, "latest_by_thread", new_callable=AsyncMock) as mock_latest:
            mock_latest.return_value = None
            checkpoint, hook = await workflow_service._maybe_compact_thread(
                MagicMock(),
                thread=thread,
                project=project,
                profile_id="default",
                history=history,
                recent_runs=[],
                request_context={},
            )

        assert checkpoint is None
        assert hook.status == "skipped"
        assert hook.meta["message_count"] == 1

    @pytest.mark.asyncio
    async def test_maybe_compact_thread_reuses_existing_checkpoint(self, workflow_service: AgentWorkflowService) -> None:
        thread = SimpleNamespace(id=uuid.uuid4())
        project = _make_project()
        history = [SimpleNamespace(content=f"消息{i}") for i in range(24)]
        recent_runs = [
            SimpleNamespace(
                id=uuid.uuid4(),
                status="completed",
                summary="已完成运行",
                updated_at=datetime.now(UTC),
            )
        ]
        total_chars = sum(len(message.content) for message in history) + len(recent_runs[0].summary)
        checkpoint = SimpleNamespace(
            id=uuid.uuid4(),
            source_message_count=len(history),
            source_run_count=len(recent_runs),
            total_context_characters=total_chars,
        )

        with patch.object(workflow_service.checkpoint_store, "latest_by_thread", new_callable=AsyncMock) as mock_latest:
            mock_latest.return_value = checkpoint
            reused_checkpoint, hook = await workflow_service._maybe_compact_thread(
                MagicMock(),
                thread=thread,
                project=project,
                profile_id="default",
                history=history,
                recent_runs=recent_runs,
                request_context={},
            )

        assert reused_checkpoint is checkpoint
        assert hook.status == "completed"
        assert hook.summary == "沿用现有 checkpoint，无需重新压缩。"

    @pytest.mark.asyncio
    async def test_maybe_compact_thread_creates_new_checkpoint(self, workflow_service: AgentWorkflowService) -> None:
        thread = SimpleNamespace(id=uuid.uuid4())
        project = _make_project()
        history = [SimpleNamespace(content=f"消息{i}" * 20) for i in range(24)]
        recent_runs = [
            SimpleNamespace(
                id=uuid.uuid4(),
                status="completed",
                summary="运行摘要",
                updated_at=datetime.now(UTC),
            )
        ]
        created_checkpoint = SimpleNamespace(id=uuid.uuid4())

        with patch.object(workflow_service.checkpoint_store, "latest_by_thread", new_callable=AsyncMock) as mock_latest:
            with patch.object(workflow_service, "_compact_policy_payload", return_value={"version": "test"}):
                with patch.object(
                    workflow_service,
                    "_active_bundle_contract_payload_for_checkpoint",
                    return_value={"source": "live_context"},
                ):
                    with patch.object(workflow_service, "_summarize_thread", return_value="压缩摘要"):
                        with patch.object(
                            workflow_service.checkpoint_store,
                            "create",
                            new_callable=AsyncMock,
                        ) as mock_create:
                            mock_latest.return_value = None
                            mock_create.return_value = created_checkpoint

                            checkpoint, hook = await workflow_service._maybe_compact_thread(
                                MagicMock(),
                                thread=thread,
                                project=project,
                                profile_id="default",
                                history=history,
                                recent_runs=recent_runs,
                                request_context={"chapter_id": str(uuid.uuid4())},
                            )

        assert checkpoint is created_checkpoint
        assert hook.status == "completed"
        assert hook.summary == "线程达到阈值，已生成新的上下文压缩 checkpoint。"
        mock_create.assert_awaited_once()


class TestNormalizeOperationPayloadBranches:
    """Covers normalization paths that were previously untested."""

    @pytest.mark.asyncio
    async def test_normalize_operation_payload_for_chapter_and_scene_variants(self, workflow_service: AgentWorkflowService) -> None:
        project_id = uuid.uuid4()
        volume = _make_volume(project_id)
        chapter = _make_chapter(project_id, volume.id, content="旧章节正文")
        scene = _make_scene(chapter.id, content="旧场景正文")

        with patch.object(workflow_service, "_resolve_chapter", new_callable=AsyncMock) as mock_resolve_chapter:
            with patch.object(workflow_service, "_resolve_scene", new_callable=AsyncMock) as mock_resolve_scene:
                with patch.object(workflow_service, "_filter_scene_create_payload", new_callable=AsyncMock) as mock_create_scene_payload:
                    with patch.object(workflow_service, "_filter_scene_update_payload", new_callable=AsyncMock) as mock_update_scene_payload:
                        mock_resolve_chapter.return_value = chapter
                        mock_resolve_scene.return_value = scene
                        mock_create_scene_payload.return_value = {
                            "chapter_id": str(chapter.id),
                            "scene_order": 2,
                            "content": "新场景正文",
                        }
                        mock_update_scene_payload.return_value = {"location": "偏殿", "content": "修订场景"}

                        normalized_update_chapter = await workflow_service._normalize_operation_payload(
                            MagicMock(),
                            project_id=project_id,
                            request_context={},
                            operation=_planned("update_chapter", {"updates": {"title": "新章名", "content": "修订正文"}}),
                        )
                        normalized_write_chapter = await workflow_service._normalize_operation_payload(
                            MagicMock(),
                            project_id=project_id,
                            request_context={},
                            operation=_planned("write_chapter_content", {"content": "追加正文", "mode": "append"}),
                        )
                        normalized_create_scene = await workflow_service._normalize_operation_payload(
                            MagicMock(),
                            project_id=project_id,
                            request_context={},
                            operation=_planned("create_scene", {"content": "ignored"}),
                        )
                        normalized_update_scene = await workflow_service._normalize_operation_payload(
                            MagicMock(),
                            project_id=project_id,
                            request_context={},
                            operation=_planned("update_scene", {"updates": {"location": "偏殿"}}),
                        )
                        normalized_write_scene = await workflow_service._normalize_operation_payload(
                            MagicMock(),
                            project_id=project_id,
                            request_context={},
                            operation=_planned("write_scene_content", {"content": "新场景正文", "mode": "replace"}),
                        )

        assert normalized_update_chapter["payload"]["chapter_id"] == str(chapter.id)
        assert normalized_update_chapter["payload"]["updates"]["title"] == "新章名"
        assert normalized_write_chapter["payload"]["content"] == "追加正文"
        assert normalized_write_chapter["target_type"] == "chapter"
        assert normalized_create_scene["payload"]["scene_order"] == 2
        assert normalized_create_scene["target_type"] == "scene"
        assert normalized_update_scene["payload"]["updates"]["location"] == "偏殿"
        assert normalized_write_scene["payload"]["scene_id"] == str(scene.id)
        assert normalized_write_scene["target_display"] == f"场景 {scene.scene_order}"

    @pytest.mark.asyncio
    async def test_normalize_operation_payload_rejects_empty_chapter_and_scene_updates(self, workflow_service: AgentWorkflowService) -> None:
        project_id = uuid.uuid4()
        chapter = _make_chapter(project_id, uuid.uuid4())
        scene = _make_scene(chapter.id)

        with patch.object(workflow_service, "_resolve_chapter", new_callable=AsyncMock) as mock_resolve_chapter:
            with patch.object(workflow_service, "_resolve_scene", new_callable=AsyncMock) as mock_resolve_scene:
                with patch.object(workflow_service, "_filter_scene_update_payload", new_callable=AsyncMock) as mock_update_scene_payload:
                    mock_resolve_chapter.return_value = chapter
                    mock_resolve_scene.return_value = scene
                    mock_update_scene_payload.return_value = {}

                    with pytest.raises(BadRequestException, match="update_chapter requires a non-empty updates object"):
                        await workflow_service._normalize_operation_payload(
                            MagicMock(),
                            project_id=project_id,
                            request_context={},
                            operation=_planned("update_chapter", {"updates": {}}),
                        )

                    with pytest.raises(BadRequestException, match="write_scene_content requires content"):
                        await workflow_service._normalize_operation_payload(
                            MagicMock(),
                            project_id=project_id,
                            request_context={},
                            operation=_planned("write_scene_content", {"content": "   "}),
                        )

                    with pytest.raises(BadRequestException, match="update_scene requires a non-empty updates object"):
                        await workflow_service._normalize_operation_payload(
                            MagicMock(),
                            project_id=project_id,
                            request_context={},
                            operation=_planned("update_scene", {"updates": {}}),
                        )


class TestExecuteOperationBranches:
    """Covers execution branches for chapter and scene operations."""

    @pytest.mark.asyncio
    async def test_execute_operation_for_chapter_and_scene_variants(self, workflow_service: AgentWorkflowService) -> None:
        project_id = uuid.uuid4()
        volume = _make_volume(project_id)
        chapter = _make_chapter(project_id, volume.id, content="旧章节正文")
        updated_chapter = _make_chapter(project_id, volume.id, content="修订章节正文")
        updated_chapter.id = chapter.id
        updated_chapter.chapter_number = chapter.chapter_number
        updated_chapter.title = "修订章名"
        written_chapter = _make_chapter(project_id, volume.id, content="旧章节正文\n\n追加正文")
        written_chapter.id = chapter.id
        written_chapter.chapter_number = chapter.chapter_number
        written_chapter.title = chapter.title

        scene = _make_scene(chapter.id, content="旧场景正文")
        updated_scene = _make_scene(chapter.id, content="修订场景正文")
        updated_scene.id = scene.id
        updated_scene.scene_order = scene.scene_order
        updated_scene.location = "偏殿"
        written_scene = _make_scene(chapter.id, content="新场景正文")
        written_scene.id = scene.id
        written_scene.scene_order = scene.scene_order

        created_chapter = _make_chapter(project_id, volume.id, chapter_number=2, title="新章节", content="新正文")
        created_scene = _make_scene(chapter.id, scene_order=2, content="新场景正文")

        db = MagicMock()
        db.flush = AsyncMock()

        with patch.object(workflow_service, "_resolve_chapter", new_callable=AsyncMock) as mock_resolve_chapter:
            with patch.object(workflow_service, "_resolve_scene", new_callable=AsyncMock) as mock_resolve_scene:
                with patch.object(workflow_service, "_create_operation_snapshot", new_callable=AsyncMock) as mock_snapshot:
                    with patch("app.services.agent_workflow.chapter_service.create_with_project", new_callable=AsyncMock) as mock_create_chapter:
                        with patch("app.services.agent_workflow.chapter_service.update", new_callable=AsyncMock) as mock_update_chapter:
                            with patch("app.services.agent_workflow.scene_service.create_with_chapter", new_callable=AsyncMock) as mock_create_scene:
                                with patch("app.services.agent_workflow.scene_service.update", new_callable=AsyncMock) as mock_update_scene:
                                    mock_resolve_chapter.side_effect = [chapter, chapter, chapter]
                                    mock_resolve_scene.side_effect = [scene, scene]
                                    mock_create_chapter.return_value = created_chapter
                                    mock_update_chapter.side_effect = [updated_chapter, written_chapter]
                                    mock_create_scene.return_value = created_scene
                                    mock_update_scene.side_effect = [updated_scene, written_scene]

                                    create_chapter_operation = _operation(
                                        "create_chapter",
                                        {"chapter_number": 2, "title": "新章节", "volume_id": str(volume.id), "content": "新正文"},
                                    )
                                    update_chapter_operation = _operation(
                                        "update_chapter",
                                        {"updates": {"title": "修订章名", "content": "修订章节正文"}},
                                    )
                                    write_chapter_operation = _operation(
                                        "write_chapter_content",
                                        {"content": "追加正文", "mode": "append"},
                                    )
                                    create_scene_operation = _operation(
                                        "create_scene",
                                        {"scene_order": 2, "content": "新场景正文"},
                                    )
                                    update_scene_operation = _operation(
                                        "update_scene",
                                        {"updates": {"location": "偏殿", "content": "修订场景正文"}},
                                    )
                                    write_scene_operation = _operation(
                                        "write_scene_content",
                                        {"content": "新场景正文", "mode": "replace"},
                                    )

                                    for operation in [
                                        create_chapter_operation,
                                        update_chapter_operation,
                                        write_chapter_operation,
                                        create_scene_operation,
                                        update_scene_operation,
                                        write_scene_operation,
                                    ]:
                                        await workflow_service._execute_operation(
                                            db,
                                            project_id=project_id,
                                            request_context={},
                                            operation=operation,
                                        )

        assert create_chapter_operation.target_id == created_chapter.id
        assert create_chapter_operation.execution_result == {"created_id": str(created_chapter.id)}
        assert update_chapter_operation.execution_result["updated_id"] == str(updated_chapter.id)
        assert "追加正文" in written_chapter.content
        assert write_chapter_operation.execution_result["updated_id"] == str(written_chapter.id)
        assert create_scene_operation.target_id == created_scene.id
        assert update_scene_operation.execution_result["updated_id"] == str(updated_scene.id)
        assert write_scene_operation.execution_result["updated_id"] == str(written_scene.id)
        assert all(operation.status == "executed" for operation in [
            create_chapter_operation,
            update_chapter_operation,
            write_chapter_operation,
            create_scene_operation,
            update_scene_operation,
            write_scene_operation,
        ])
        assert mock_snapshot.await_count == 6
        assert db.flush.await_count == 6

    @pytest.mark.asyncio
    async def test_execute_operation_rejects_unsupported_tool(self, workflow_service: AgentWorkflowService) -> None:
        db = MagicMock()
        db.flush = AsyncMock()

        with pytest.raises(BadRequestException, match="Unsupported tool 'unsupported_tool'"):
            await workflow_service._execute_operation(
                db,
                project_id=uuid.uuid4(),
                request_context={},
                operation=_operation("unsupported_tool", {}),
            )


class TestVerificationHelpers:
    """Covers content, semantic, domain, and target-loading verification helpers."""

    def test_verify_operation_content_transition_and_snapshot_semantics(self, workflow_service: AgentWorkflowService) -> None:
        project_id = uuid.uuid4()
        volume = _make_volume(project_id)
        chapter = _make_chapter(project_id, volume.id, title="旧标题", content="旧正文")

        write_operation = _operation("write_chapter_content", {"content": "追加正文", "mode": "append"})
        snapshot = SimpleNamespace(data={"content": "旧正文"})
        ok, summary = workflow_service._verify_operation_content_transition(
            operation=write_operation,
            snapshot=snapshot,
            target=_make_chapter(project_id, volume.id, title="旧标题", content="旧正文\n\n追加正文"),
        )
        assert ok is True
        assert summary == "内容迁移已校验：append"

        failed, failure_summary = workflow_service._verify_operation_content_transition(
            operation=write_operation,
            snapshot=snapshot,
            target=_make_chapter(project_id, volume.id, title="旧标题", content="错误正文"),
        )
        assert failed is False
        assert "内容迁移不一致" in failure_summary

        update_operation = _operation("update_chapter", {"updates": {"title": "新标题"}})
        update_operation.execution_result = {"snapshot_verification": {"stage": "pre_update"}}
        semantic_snapshot = SimpleNamespace(data={"project_id": str(project_id), "volume_id": str(volume.id), "chapter_number": 1, "title": "旧标题", "outline": "章纲", "content": "旧正文", "status": "draft", "notes": "章备注"})

        passed, passed_summary = workflow_service._verify_operation_snapshot_semantics(
            operation=update_operation,
            snapshot=semantic_snapshot,
            target=_make_chapter(project_id, volume.id, title="新标题", content="旧正文"),
        )
        assert passed is True
        assert passed_summary == "快照语义已校验：pre_update"

        failed_semantic, failed_summary = workflow_service._verify_operation_snapshot_semantics(
            operation=update_operation,
            snapshot=semantic_snapshot,
            target=_make_chapter(project_id, volume.id, title="另一标题", content="旧正文"),
        )
        assert failed_semantic is False
        assert "快照语义不一致" in failed_summary

    @pytest.mark.asyncio
    async def test_verify_operation_domain_semantics_across_targets(self, workflow_service: AgentWorkflowService) -> None:
        project_id = uuid.uuid4()
        other_project_id = uuid.uuid4()
        project = _make_project(project_id, story_outline="有效大纲")
        empty_outline_project = _make_project(project_id, story_outline="   ")
        volume = _make_volume(project_id, volume_number=1)
        chapter = _make_chapter(project_id, volume.id, chapter_number=1)
        other_project_character = _make_character(other_project_id)

        db = MagicMock()
        db.execute = AsyncMock(
            side_effect=[
                FakeScalarResult(None),  # character duplicate pass
                FakeScalarResult(uuid.uuid4()),  # character duplicate fail
                FakeScalarResult(None),  # setting duplicate pass
                FakeScalarResult(uuid.uuid4()),  # setting duplicate fail
                FakeScalarResult(None),  # volume duplicate pass
                FakeScalarResult(uuid.uuid4()),  # volume duplicate fail
                FakeScalarResult(None),  # chapter duplicate pass
                FakeScalarResult(uuid.uuid4()),  # chapter duplicate fail
                FakeScalarResult(None),  # scene duplicate pass
                FakeScalarResult(uuid.uuid4()),  # scene duplicate fail
            ]
        )

        with patch("app.services.agent_workflow.volume_service.get", new_callable=AsyncMock) as mock_get_volume:
            with patch("app.services.agent_workflow.chapter_service.get", new_callable=AsyncMock) as mock_get_chapter:
                with patch("app.services.agent_workflow.character_service.get", new_callable=AsyncMock) as mock_get_character:
                    mock_get_volume.side_effect = [volume, NotFoundException("missing volume")]
                    mock_get_chapter.side_effect = [chapter, NotFoundException("missing chapter")]
                    mock_get_character.side_effect = [
                        _make_character(project_id),
                        other_project_character,
                    ]

                    project_pass = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("update_project_outline", {}),
                        target=project,
                    )
                    project_fail = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("update_project_outline", {}),
                        target=empty_outline_project,
                    )
                    character_pass = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("create_character", {}),
                        target=_make_character(project_id, age=18),
                    )
                    character_fail = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("update_character", {}),
                        target=_make_character(project_id, name="   ", age=-1),
                    )
                    setting_pass = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("create_world_setting", {}),
                        target=_make_setting(project_id),
                    )
                    setting_fail = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("update_world_setting", {}),
                        target=_make_setting(project_id, name="   ", content="  "),
                    )
                    volume_pass = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("create_volume", {}),
                        target=volume,
                    )
                    volume_fail = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("update_volume", {}),
                        target=_make_volume(other_project_id, volume_number=1),
                    )
                    chapter_pass = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("create_chapter", {}),
                        target=chapter,
                    )
                    chapter_fail = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("update_chapter", {}),
                        target=_make_chapter(project_id, volume.id, chapter_number=1),
                    )
                    scene_pass = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("create_scene", {}),
                        target=_make_scene(chapter.id, scene_order=1, pov_character_id=_make_character(project_id).id),
                    )
                    scene_fail = await workflow_service._verify_operation_domain_semantics(
                        db,
                        project_id=project_id,
                        operation=_operation("update_scene", {}),
                        target=_make_scene(chapter.id, scene_order=1, pov_character_id=other_project_character.id),
                    )

        assert project_pass == (True, "领域语义已校验：story_outline_not_empty")
        assert project_fail[0] is False and "项目大纲不能为空" in project_fail[1]
        assert character_pass[0] is True and "character_name_unique" in character_pass[1]
        assert character_fail[0] is False and "人物名称重复" in character_fail[1]
        assert setting_pass[0] is True and "world_setting_name_unique" in setting_pass[1]
        assert setting_fail[0] is False and "设定名称不能为空" in setting_fail[1]
        assert volume_pass[0] is True and "volume_number_unique" in volume_pass[1]
        assert volume_fail[0] is False and "卷序号重复" in volume_fail[1]
        assert chapter_pass[0] is True and "chapter_number_unique" in chapter_pass[1]
        assert chapter_fail[0] is False and "卷不存在" in chapter_fail[1]
        assert scene_pass[0] is True and "scene_order_unique" in scene_pass[1]
        assert scene_fail[0] is False and "场景父章节缺失" in scene_fail[1]

    @pytest.mark.asyncio
    async def test_expected_target_loading_summary_and_verification_aggregation(self, workflow_service: AgentWorkflowService) -> None:
        project_id = uuid.uuid4()
        volume = _make_volume(project_id, title="卷一")
        chapter = _make_chapter(project_id, volume.id, title="第一章", content="章节正文")
        scene = _make_scene(chapter.id, content="场景正文")

        update_operation = _operation("update_scene", {"updates": {"location": "偏殿", "content": "不应进入 expected_updates"}})
        expected_updates = workflow_service._field_level_expected_updates(update_operation)
        assert expected_updates == {"location": "偏殿"}

        snapshot = SimpleNamespace(data={"title": "旧标题", "content": "旧内容"})
        expected_from_snapshot = workflow_service._expected_target_from_snapshot(
            operation=_operation("write_chapter_content", {"content": "新内容", "mode": "replace"}),
            snapshot=snapshot,
        )
        assert expected_from_snapshot["content"] == "新内容"

        with patch.object(workflow_service, "_resolve_chapter", new_callable=AsyncMock) as mock_resolve_chapter:
            with patch.object(workflow_service, "_resolve_scene", new_callable=AsyncMock) as mock_resolve_scene:
                mock_resolve_chapter.return_value = chapter
                mock_resolve_scene.return_value = scene

                loaded_chapter = await workflow_service._load_operation_target(
                    MagicMock(),
                    project_id=project_id,
                    operation=_operation("write_chapter_content", {"content": "新内容"}, target_id=chapter.id),
                )
                loaded_scene = await workflow_service._load_operation_target(
                    MagicMock(),
                    project_id=project_id,
                    operation=_operation("write_scene_content", {"content": "新场景"}, target_id=scene.id),
                )

        assert loaded_chapter is chapter
        assert loaded_scene is scene
        assert workflow_service._target_summary(chapter, "write_chapter_content") == "章节正文"
        assert workflow_service._target_summary(scene, "write_scene_content") == "场景正文"
        assert workflow_service._snapshot_semantic_fields(
            operation=_operation("update_scene", {}),
            target=scene,
        ) == ["chapter_id", "scene_order", "pov_character_id", "location", "content", "meta"]

        failed_status, failed_summary = workflow_service._aggregate_run_verification(
            [
                SimpleNamespace(
                    verification_status=AgentVerificationStatus.FAILED.value,
                    description="更新章节",
                )
            ],
            continuity_subtask=None,
        )
        skipped_status, skipped_summary = workflow_service._aggregate_run_verification(
            [],
            continuity_subtask=None,
        )
        continuity_status, continuity_summary = workflow_service._aggregate_run_verification(
            [SimpleNamespace(verification_status=AgentVerificationStatus.PASSED.value, description="更新场景")],
            continuity_subtask=SimpleNamespace(
                status=AgentSubtaskStatus.FAILED.value,
                error_message="Continuity gate failed.",
            ),
        )

        assert failed_status == AgentVerificationStatus.FAILED.value
        assert "更新章节" in failed_summary
        assert skipped_status == AgentVerificationStatus.SKIPPED.value
        assert skipped_summary == "No stateful operations to verify."
        assert continuity_status == AgentVerificationStatus.FAILED.value
        assert continuity_summary == "Continuity gate failed."
