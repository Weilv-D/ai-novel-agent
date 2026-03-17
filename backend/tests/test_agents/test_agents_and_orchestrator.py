"""Unit coverage for lightweight agents and the writing orchestrator."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.character_agent import CharacterAgent
from app.agents.continuity_agent import ContinuityAgent
from app.agents.draft_agent import DraftAgent
from app.agents.lore_agent import LoreAgent
from app.agents.orchestrator import WritingOrchestrator
from app.agents.outline_agent import OutlineAgent


class DummyAgent(BaseAgent):
    """Concrete agent for exercising shared BaseAgent helpers."""

    def build_system_prompt(self, context: AgentContext) -> str:
        return f"system:{context.project_id}"

    async def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(message=context.user_message)


class FakeMemory:
    """Lightweight stand-in for Memory ORM objects in auto-summarize tests."""

    def __init__(self, **kwargs: object) -> None:
        self.id: uuid.UUID | None = None
        for key, value in kwargs.items():
            setattr(self, key, value)


async def _iterate(chunks: list[str]) -> AsyncIterator[str]:
    """Yield chunks as an async iterator."""
    for chunk in chunks:
        yield chunk


class TestBaseAgent:
    """Covers message shaping and JSON extraction helpers on BaseAgent."""

    @pytest.mark.asyncio
    async def test_call_llm_uses_last_ten_messages_and_custom_prompt(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(return_value={"content": "完成"})
        agent = DummyAgent(llm=llm)
        context = AgentContext(
            project_id="project-1",
            user_message="当前请求",
            history=[{"role": "user", "content": f"消息{i}"} for i in range(12)],
        )

        result = await agent._call_llm(context, system_prompt="custom prompt", temperature=0.2)

        assert result == "完成"
        llm.generate.assert_awaited_once()
        messages = llm.generate.await_args.args[0]
        assert messages[0] == {"role": "system", "content": "custom prompt"}
        assert len(messages) == 12
        assert messages[1]["content"] == "消息2"
        assert messages[-1] == {"role": "user", "content": "当前请求"}
        assert llm.generate.await_args.kwargs["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_call_llm_stream_uses_built_system_prompt(self) -> None:
        llm = MagicMock()
        llm.generate_stream = MagicMock(return_value=_iterate(["甲", "乙"]))
        agent = DummyAgent(llm=llm)
        context = AgentContext(project_id="project-2", user_message="流式消息")

        chunks = [chunk async for chunk in agent._call_llm_stream(context, temperature=0.1)]

        assert chunks == ["甲", "乙"]
        llm.generate_stream.assert_called_once()
        messages = llm.generate_stream.call_args.args[0]
        assert messages == [
            {"role": "system", "content": "system:project-2"},
            {"role": "user", "content": "流式消息"},
        ]
        assert llm.generate_stream.call_args.kwargs["temperature"] == 0.1

    def test_parse_json_from_response_handles_code_blocks_bare_json_and_invalid(self, caplog: pytest.LogCaptureFixture) -> None:
        agent = DummyAgent(llm=MagicMock())

        assert agent._parse_json_from_response("```json\n{\"ok\": true}\n```") == {"ok": True}
        assert agent._parse_json_from_response("前缀 {\"tool\": \"create\"}") == {"tool": "create"}

        with caplog.at_level("WARNING"):
            assert agent._parse_json_from_response("无可解析内容") is None
        assert "Failed to parse JSON" in caplog.text


class TestSpecializedAgents:
    """Covers prompt construction and suggestion extraction for specialized agents."""

    @pytest.mark.asyncio
    async def test_character_agent_prompt_and_run(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value={
                "content": "```json\n"
                "{\"action\":\"character_edit\",\"character_name\":\"苏砚\",\"field\":\"notes\",\"suggested_value\":\"更沉稳\",\"reason\":\"补充人物弧光\"}\n"
                "```"
            }
        )
        agent = CharacterAgent(llm=llm)
        context = AgentContext(
            project_id="p1",
            user_message="完善人物",
            context_data={
                "characters": [
                    {"name": "苏砚", "role": "主角", "profile": {"description": "少年修士"}},
                ]
            },
        )

        prompt = agent.build_system_prompt(context)
        result = await agent.run(context)

        assert "苏砚" in prompt
        assert "character_edit" in prompt
        assert result.metadata == {"agent": "character"}
        assert result.suggestions == [
            {
                "type": "character_edit",
                "target_type": "character",
                "content": {
                    "action": "character_edit",
                    "character_name": "苏砚",
                    "field": "notes",
                    "suggested_value": "更沉稳",
                    "reason": "补充人物弧光",
                },
            }
        ]

    @pytest.mark.asyncio
    async def test_continuity_agent_prompt_and_run_normalizes_unknown_target(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value={
                "content": "{\"action\":\"continuity_fix\",\"issue\":\"法则冲突\",\"target_type\":\"unknown\",\"suggested_fix\":\"统一法则描述\",\"severity\":\"high\"}"
            }
        )
        agent = ContinuityAgent(llm=llm)
        context = AgentContext(
            project_id="p2",
            user_message="检查连续性",
            context_data={
                "characters": [{"name": "苏砚", "role": "主角"}],
                "world_settings": [{"name": "灵气体系"}],
                "chapters": [{"chapter_number": 3}],
                "memories": [{"content": "第三章曾明确写到不能御剑"}],
            },
        )

        prompt = agent.build_system_prompt(context)
        result = await agent.run(context)

        assert "人物: 苏砚 (主角)" in prompt
        assert "已知事实" in prompt
        assert result.metadata == {"agent": "continuity"}
        assert result.suggestions[0]["target_type"] == "chapter"

    @pytest.mark.asyncio
    async def test_draft_agent_prompt_and_run(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value={
                "content": "{\"action\":\"content_gen\",\"content\":\"新场景内容\",\"word_count\":320,\"notes\":\"推进冲突\"}"
            }
        )
        agent = DraftAgent(llm=llm)
        context = AgentContext(
            project_id="p3",
            user_message="续写场景",
            context_data={
                "current_scene": {"location": "山门", "content": "旧片段"},
                "current_chapter": {"chapter_number": 5, "title": "夜探"},
                "characters": [{"name": "苏砚"}, {"name": "陆衡"}],
            },
        )

        prompt = agent.build_system_prompt(context)
        result = await agent.run(context)

        assert "当前场景" in prompt
        assert "相关人物: 苏砚, 陆衡" in prompt
        assert result.metadata == {"agent": "draft"}
        assert result.suggestions[0]["type"] == "content_gen"
        assert result.suggestions[0]["target_type"] == "scene"

    @pytest.mark.asyncio
    async def test_lore_agent_prompt_and_run(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value={
                "content": "{\"action\":\"world_edit\",\"target_name\":\"灵气体系\",\"category\":\"magic_system\",\"suggested_content\":\"灵气分九阶\",\"reason\":\"补全体系层次\"}"
            }
        )
        agent = LoreAgent(llm=llm)
        context = AgentContext(
            project_id="p4",
            user_message="完善设定",
            context_data={
                "world_settings": [
                    {"category": "magic_system", "name": "灵气体系", "content": "天地有灵"},
                ]
            },
        )

        prompt = agent.build_system_prompt(context)
        result = await agent.run(context)

        assert "[magic_system] 灵气体系" in prompt
        assert result.metadata == {"agent": "lore"}
        assert result.suggestions[0]["target_type"] == "world_setting"

    @pytest.mark.asyncio
    async def test_outline_agent_prompt_and_run(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value={
                "content": "{\"action\":\"chapter_edit\",\"target_type\":\"chapter\",\"chapter_number\":2,\"field\":\"outline\",\"suggested_value\":\"冲突升级\",\"reason\":\"提升节奏\"}"
            }
        )
        agent = OutlineAgent(llm=llm)
        context = AgentContext(
            project_id="p5",
            user_message="调整章纲",
            context_data={
                "project": {"genre": "Fantasy", "target_word_count": 80000, "story_outline": "少年入山"},
                "volumes": [{"volume_number": 1, "title": "卷一", "outline": "入门"}],
                "chapters": [{"chapter_number": 2, "title": "初试锋芒", "outline": "比试"}],
            },
        )

        prompt = agent.build_system_prompt(context)
        result = await agent.run(context)

        assert "类型: Fantasy" in prompt
        assert "第1卷 卷一" in prompt
        assert "第2章 初试锋芒" in prompt
        assert result.metadata == {"agent": "outline"}
        assert result.suggestions[0]["type"] == "chapter_edit"


class TestWritingOrchestrator:
    """Covers routing, context loading, persistence, and helper branches."""

    def test_get_agent_caches_instances_and_falls_back_to_draft(self) -> None:
        orchestrator = WritingOrchestrator(llm=MagicMock())

        lore_agent = orchestrator._get_agent("lore")
        assert lore_agent is orchestrator._get_agent("lore")
        assert isinstance(lore_agent, LoreAgent)
        assert isinstance(orchestrator._get_agent("unknown"), DraftAgent)

    @pytest.mark.asyncio
    async def test_classify_accepts_known_agent_and_falls_back_to_draft(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=[{"content": "outline"}, {"content": "mystery"}])
        orchestrator = WritingOrchestrator(llm=llm)

        assert await orchestrator.classify("规划章节") == "outline"
        assert await orchestrator.classify("未知需求") == "draft"

    @pytest.mark.asyncio
    async def test_load_context_collects_entities_and_tolerates_failures(self) -> None:
        orchestrator = WritingOrchestrator(llm=MagicMock())
        project_id = str(uuid.uuid4())
        chapter_id = uuid.uuid4()

        with patch("app.services.project.project_service.get", new_callable=AsyncMock) as mock_project:
            with patch("app.agents.orchestrator.character_service.get_by_project", new_callable=AsyncMock) as mock_characters:
                with patch("app.agents.orchestrator.world_setting_service.get_by_project", new_callable=AsyncMock) as mock_world_settings:
                    with patch("app.agents.orchestrator.volume_service.get_by_project", new_callable=AsyncMock) as mock_volumes:
                        with patch("app.agents.orchestrator.chapter_service.get_by_project", new_callable=AsyncMock) as mock_chapters:
                            with patch("app.agents.orchestrator.memory_service.get_by_project", new_callable=AsyncMock) as mock_memories:
                                mock_project.return_value = SimpleNamespace(
                                    id=uuid.UUID(project_id),
                                    name="测试项目",
                                    genre="Fantasy",
                                    target_word_count=120000,
                                    summary="摘要",
                                    story_outline="大纲",
                                )
                                mock_characters.side_effect = RuntimeError("character lookup failed")
                                mock_world_settings.return_value = [
                                    SimpleNamespace(id=uuid.uuid4(), category="rules", name="禁术", content="不可越级施法"),
                                ]
                                mock_volumes.return_value = [
                                    SimpleNamespace(id=uuid.uuid4(), volume_number=1, title="卷一", outline="开端"),
                                ]
                                mock_chapters.return_value = [
                                    SimpleNamespace(id=chapter_id, volume_id=None, chapter_number=1, title="序章", outline="引子", status="draft"),
                                ]
                                mock_memories.side_effect = RuntimeError("memory lookup failed")

                                context = await orchestrator.load_context(
                                    MagicMock(),
                                    project_id,
                                    extra={"current_scene": {"id": "scene-1"}},
                                )

        assert context["project"]["name"] == "测试项目"
        assert context["characters"] == []
        assert context["world_settings"][0]["name"] == "禁术"
        assert context["volumes"][0]["title"] == "卷一"
        assert context["chapters"][0]["id"] == str(chapter_id)
        assert context["memories"] == []
        assert context["current_scene"] == {"id": "scene-1"}

    @pytest.mark.asyncio
    async def test_chat_runs_agent_and_persists_each_suggestion(self) -> None:
        llm = MagicMock()
        orchestrator = WritingOrchestrator(llm=llm)
        first_target = uuid.uuid4()
        second_target = uuid.uuid4()
        agent = MagicMock()
        agent.run = AsyncMock(
            return_value=AgentResult(
                message="处理完成",
                suggestions=[
                    {"target_type": "project", "type": "outline_gen", "content": {"outline": "新大纲"}},
                    {"target_type": "character", "type": "character_edit", "content": {"field": "notes"}},
                ],
                metadata={"source": "unit"},
            )
        )

        with patch.object(orchestrator, "classify", new_callable=AsyncMock) as mock_classify:
            with patch.object(orchestrator, "load_context", new_callable=AsyncMock) as mock_load_context:
                with patch.object(orchestrator, "_get_agent", return_value=agent):
                    with patch.object(orchestrator, "_resolve_target_id", side_effect=[first_target, second_target]):
                        with patch("app.agents.orchestrator.suggestion_service.create_with_project", new_callable=AsyncMock) as mock_create:
                            mock_classify.return_value = "outline"
                            mock_load_context.return_value = {
                                "project": {"id": str(uuid.uuid4())},
                                "characters": [{"id": str(second_target), "name": "苏砚"}],
                            }

                            result = await orchestrator.chat(
                                MagicMock(),
                                project_id=str(uuid.uuid4()),
                                user_message="帮我规划",
                                history=[{"role": "user", "content": "上文"}],
                            )

        assert result.message == "处理完成"
        assert result.metadata == {"source": "unit", "agent_type": "outline"}
        assert mock_create.await_count == 2
        created_payload = mock_create.await_args_list[0].kwargs["obj_in"]
        assert created_payload.target_id == first_target
        assert created_payload.type == "outline_gen"

    @pytest.mark.asyncio
    async def test_chat_stream_yields_chunks_and_appends_suggestion_event(self) -> None:
        orchestrator = WritingOrchestrator(llm=MagicMock())
        suggestion_id = uuid.uuid4()
        agent = MagicMock()
        agent._call_llm_stream = MagicMock(return_value=_iterate(["片段A", "片段B"]))
        agent._parse_json_from_response.return_value = {"action": "world_edit", "target_name": "灵气体系"}

        with patch.object(orchestrator, "classify", new_callable=AsyncMock) as mock_classify:
            with patch.object(orchestrator, "load_context", new_callable=AsyncMock) as mock_load_context:
                with patch.object(orchestrator, "_get_agent", return_value=agent):
                    with patch.object(orchestrator, "_resolve_target_id", return_value=uuid.uuid4()):
                        with patch("app.agents.orchestrator.suggestion_service.create_with_project", new_callable=AsyncMock) as mock_create:
                            mock_classify.return_value = "lore"
                            mock_load_context.return_value = {"world_settings": [{"id": str(uuid.uuid4()), "name": "灵气体系"}]}
                            mock_create.return_value = SimpleNamespace(id=suggestion_id)

                            chunks = [
                                chunk
                                async for chunk in orchestrator.chat_stream(
                                    MagicMock(),
                                    project_id=str(uuid.uuid4()),
                                    user_message="补全设定",
                                )
                            ]

        assert chunks == ["片段A", "片段B", f"\n[SUGGESTION:{suggestion_id}]"]
        created_payload = mock_create.await_args.kwargs["obj_in"]
        assert created_payload.target_type == "world_setting"
        assert created_payload.type == "world_edit"

    @pytest.mark.asyncio
    async def test_auto_summarize_creates_memories_and_skips_invalid_entries(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(
            return_value={
                "content": """
分析结果：
[
  {"memory_type": "episode", "content": "主角夜探山门。"},
  "ignore me",
  {"memory_type": "unsupported", "content": "世界存在护山阵法。"}
]
"""
            }
        )
        llm.embed_single = AsyncMock(side_effect=[[0.1, 0.2], [0.3, 0.4]])
        orchestrator = WritingOrchestrator(llm=llm)
        db = MagicMock()
        db.flush = AsyncMock()

        async def _refresh(memory: object) -> None:
            memory.id = uuid.uuid4()

        db.refresh = AsyncMock(side_effect=_refresh)

        with patch("app.models.memory.Memory", FakeMemory):
            memories = await orchestrator.auto_summarize(
                db,
                project_id=str(uuid.uuid4()),
                chapter_id=str(uuid.uuid4()),
                content="章节内容",
            )

        assert len(memories) == 2
        assert memories[0]["memory_type"] == "episode"
        assert memories[1]["memory_type"] == "fact"
        assert db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_auto_summarize_returns_empty_when_response_lacks_json_array(self) -> None:
        llm = MagicMock()
        llm.generate = AsyncMock(return_value={"content": "没有可解析内容"})
        orchestrator = WritingOrchestrator(llm=llm)

        memories = await orchestrator.auto_summarize(
            MagicMock(),
            project_id=str(uuid.uuid4()),
            chapter_id=str(uuid.uuid4()),
            content="章节内容",
        )

        assert memories == []

    @pytest.mark.asyncio
    async def test_continuity_check_delegates_to_continuity_agent(self) -> None:
        orchestrator = WritingOrchestrator(llm=MagicMock())
        agent = MagicMock()
        agent.run = AsyncMock(return_value=AgentResult(message="通过", metadata={"agent": "continuity"}))

        with patch.object(orchestrator, "load_context", new_callable=AsyncMock) as mock_load_context:
            with patch.object(orchestrator, "_get_agent", return_value=agent):
                mock_load_context.return_value = {"characters": [{"name": "苏砚"}]}
                result = await orchestrator.continuity_check(
                    MagicMock(),
                    project_id=str(uuid.uuid4()),
                    content="第一章内容",
                )

        assert result.message == "通过"
        agent.run.assert_awaited_once()
        ctx = agent.run.await_args.args[0]
        assert "请检查以下内容的连续性和一致性问题" in ctx.user_message
        assert ctx.context_data["characters"][0]["name"] == "苏砚"

    def test_resolve_target_id_prefers_exact_matches_then_falls_back(self) -> None:
        orchestrator = WritingOrchestrator(llm=MagicMock())
        project_id = uuid.uuid4()
        character_id = uuid.uuid4()
        world_setting_id = uuid.uuid4()
        chapter_id = uuid.uuid4()
        volume_id = uuid.uuid4()
        fallback_chapter_id = uuid.uuid4()
        context_data = {
            "project": {"id": str(project_id)},
            "characters": [{"id": str(character_id), "name": "苏砚"}],
            "world_settings": [{"id": str(world_setting_id), "name": "灵气体系"}],
            "chapters": [
                {"id": str(chapter_id), "chapter_number": 2},
                {"id": str(fallback_chapter_id), "chapter_number": 3},
            ],
            "volumes": [{"id": str(volume_id), "volume_number": 1, "title": "卷一"}],
        }

        assert orchestrator._resolve_target_id(
            {"target_type": "character", "content": {"character_name": "苏砚"}},
            context_data,
        ) == character_id
        assert orchestrator._resolve_target_id(
            {"target_type": "world_setting", "content": {"target_name": "灵气体系"}},
            context_data,
        ) == world_setting_id
        assert orchestrator._resolve_target_id(
            {"target_type": "chapter", "content": {"chapter_number": 2}},
            context_data,
        ) == chapter_id
        assert orchestrator._resolve_target_id(
            {"target_type": "project", "content": {}},
            context_data,
        ) == project_id
        assert orchestrator._resolve_target_id(
            {"target_type": "volume", "content": {"volume_title": "卷一"}},
            context_data,
        ) == volume_id
        assert orchestrator._resolve_target_id(
            {"target_type": "chapter", "content": {}},
            context_data,
        ) == chapter_id
        assert isinstance(
            orchestrator._resolve_target_id({"target_type": "scene", "content": {}}, context_data),
            uuid.UUID,
        )
