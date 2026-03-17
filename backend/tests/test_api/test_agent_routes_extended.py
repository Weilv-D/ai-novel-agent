"""Direct route tests for the legacy and planner Agent API wrappers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1 import agent as agent_api
from app.schemas.agent import (
    AgentChatRequest,
    AgentStreamEvent,
    AgentThreadCreateRequest,
    AgentThreadMessageRequest,
    AutoSummarizeRequest,
    ContinuityCheckRequest,
    InlineEditRequest,
)


async def _collect_streaming_response(response) -> list[str]:
    """Collect all chunks from a StreamingResponse body iterator."""
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return chunks


class TestAgentRoutesExtended:
    """Covers thin route wrappers and SSE generation branches."""

    @pytest.mark.asyncio
    async def test_chunk_text_and_simple_delegating_routes(self) -> None:
        project_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        run_id = uuid.uuid4()
        sentinel = object()

        assert agent_api._chunk_text("abcdef", size=2) == ["ab", "cd", "ef"]
        assert agent_api._chunk_text("", size=2) == [""]

        with patch.object(agent_api.agent_workflow_service, "get_or_create_thread_response", new_callable=AsyncMock) as mock_thread:
            with patch.object(agent_api.agent_workflow_service, "get_thread_state_response", new_callable=AsyncMock) as mock_state:
                with patch.object(agent_api.agent_workflow_service, "get_profile_catalog_response", new_callable=AsyncMock) as mock_profiles:
                    with patch.object(agent_api.agent_workflow_service, "get_capability_registry_response", new_callable=AsyncMock) as mock_caps:
                        with patch.object(agent_api.agent_workflow_service, "get_risk_policy_registry_response", new_callable=AsyncMock) as mock_risk:
                            with patch.object(agent_api.agent_workflow_service, "get_skill_catalog_response", new_callable=AsyncMock) as mock_skills:
                                with patch.object(agent_api.agent_workflow_service, "get_run_response", new_callable=AsyncMock) as mock_run:
                                    with patch.object(agent_api.agent_workflow_service, "confirm_run_response", new_callable=AsyncMock) as mock_confirm:
                                        with patch.object(agent_api.agent_workflow_service, "confirm_high_risk_run_response", new_callable=AsyncMock) as mock_high_risk:
                                            with patch.object(agent_api.agent_workflow_service, "cancel_run_response", new_callable=AsyncMock) as mock_cancel:
                                                mock_thread.return_value = sentinel
                                                mock_state.return_value = sentinel
                                                mock_profiles.return_value = [sentinel]
                                                mock_caps.return_value = sentinel
                                                mock_risk.return_value = sentinel
                                                mock_skills.return_value = sentinel
                                                mock_run.return_value = sentinel
                                                mock_confirm.return_value = sentinel
                                                mock_high_risk.return_value = sentinel
                                                mock_cancel.return_value = sentinel

                                                assert await agent_api.create_or_get_thread(
                                                    db=MagicMock(),
                                                    req=AgentThreadCreateRequest(project_id=project_id),
                                                ) is sentinel
                                                assert await agent_api.get_thread(db=MagicMock(), thread_id=thread_id) is sentinel
                                                assert await agent_api.list_agent_profiles() == [sentinel]
                                                assert await agent_api.get_agent_capabilities() is sentinel
                                                assert await agent_api.get_agent_risk_policies(
                                                    db=MagicMock(),
                                                    project_id=project_id,
                                                    profile_id="default",
                                                ) is sentinel
                                                assert await agent_api.get_agent_skills(db=MagicMock(), project_id=project_id) is sentinel
                                                assert await agent_api.get_run(db=MagicMock(), run_id=run_id) is sentinel
                                                assert await agent_api.confirm_run(db=MagicMock(), run_id=run_id) is sentinel
                                                assert await agent_api.confirm_high_risk_run(db=MagicMock(), run_id=run_id) is sentinel
                                                assert await agent_api.cancel_run(db=MagicMock(), run_id=run_id) is sentinel

    @pytest.mark.asyncio
    async def test_create_thread_message_non_stream_and_stream_success(self) -> None:
        thread_id = uuid.uuid4()
        sentinel = object()

        with patch.object(agent_api.agent_workflow_service, "create_planned_run", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = sentinel
            assert await agent_api.create_thread_message(
                db=MagicMock(),
                thread_id=thread_id,
                req=AgentThreadMessageRequest(content="规划一下"),
            ) is sentinel

        async def _events():
            yield AgentStreamEvent(type="status", stage="planning", message="开始", detail={"step": 1})

        with patch.object(agent_api.agent_workflow_service, "stream_planned_run", return_value=_events()):
            response = await agent_api.create_thread_message(
                db=MagicMock(),
                thread_id=thread_id,
                req=AgentThreadMessageRequest(content="规划一下", stream=True),
            )
            chunks = await _collect_streaming_response(response)

        assert '"type": "status"' in chunks[0]
        assert chunks[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_create_thread_message_stream_emits_error_event_on_exception(self) -> None:
        thread_id = uuid.uuid4()

        async def _broken_events():
            raise RuntimeError("boom")
            yield  # pragma: no cover

        with patch.object(agent_api.agent_workflow_service, "stream_planned_run", return_value=_broken_events()):
            with patch.object(agent_api.logger, "error") as mock_log_error:
                response = await agent_api.create_thread_message(
                    db=MagicMock(),
                    thread_id=thread_id,
                    req=AgentThreadMessageRequest(content="规划一下", stream=True),
                )
                chunks = await _collect_streaming_response(response)

        assert '"type": "error"' in chunks[0]
        assert chunks[-1] == "data: [DONE]\n\n"
        mock_log_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_legacy_chat_routes_delegate_and_stream_chunks(self) -> None:
        project_id = uuid.uuid4()
        chat_result = SimpleNamespace(message="回复", suggestions=[{"type": "outline_gen"}], metadata={"agent": "outline"})

        async def _chat_chunks():
            yield "片段A"
            yield "片段B"

        with patch.object(agent_api.orchestrator, "chat", new_callable=AsyncMock) as mock_chat:
            with patch.object(agent_api.orchestrator, "chat_stream", return_value=_chat_chunks()):
                mock_chat.return_value = chat_result

                response = await agent_api.agent_chat(
                    db=MagicMock(),
                    req=AgentChatRequest(project_id=project_id, message="写个大纲"),
                )
                stream = await agent_api.agent_chat_stream(
                    db=MagicMock(),
                    req=AgentChatRequest(project_id=project_id, message="写个大纲"),
                )
                chunks = await _collect_streaming_response(stream)

        assert response.message == "回复"
        assert response.suggestions == [{"type": "outline_gen"}]
        assert '"content": "片段A"' in chunks[0]
        assert chunks[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_auto_summarize_and_continuity_routes_delegate(self) -> None:
        project_id = uuid.uuid4()
        chapter_id = uuid.uuid4()
        memories = [{"id": str(uuid.uuid4()), "content": "主角夜探山门。", "memory_type": "episode"}]
        continuity_result = SimpleNamespace(message="通过", suggestions=[], metadata={"agent": "continuity"})

        with patch.object(agent_api.orchestrator, "auto_summarize", new_callable=AsyncMock) as mock_auto:
            with patch.object(agent_api.orchestrator, "continuity_check", new_callable=AsyncMock) as mock_continuity:
                mock_auto.return_value = memories
                mock_continuity.return_value = continuity_result

                auto_response = await agent_api.auto_summarize(
                    db=MagicMock(),
                    req=AutoSummarizeRequest(project_id=project_id, chapter_id=chapter_id, content="章节内容"),
                )
                continuity_response = await agent_api.continuity_check(
                    db=MagicMock(),
                    req=ContinuityCheckRequest(project_id=project_id, content="章节内容"),
                )

        assert auto_response.count == 1
        assert auto_response.memories == memories
        assert continuity_response.message == "通过"
        assert continuity_response.metadata == {"agent": "continuity"}

    @pytest.mark.asyncio
    async def test_inline_edit_stream_success_and_error(self) -> None:
        async def _chunks():
            yield "改"
            yield "写结果"

        with patch.object(agent_api.llm_service, "generate_stream", return_value=_chunks()):
            response = await agent_api.inline_edit(
                req=InlineEditRequest(
                    text="原文",
                    operation="rewrite",
                    context={"chapter_title": "雨夜"},
                )
            )
            chunks = await _collect_streaming_response(response)

        assert '"content": "改"' in chunks[0]
        assert chunks[-1] == "data: [DONE]\n\n"

        async def _broken_chunks():
            raise RuntimeError("boom")
            yield  # pragma: no cover

        with patch.object(agent_api.llm_service, "generate_stream", return_value=_broken_chunks()):
            with patch.object(agent_api.logger, "error") as mock_log_error:
                response = await agent_api.inline_edit(
                    req=InlineEditRequest(text="原文", operation="condense")
                )
                chunks = await _collect_streaming_response(response)

        assert '"type": "error"' in chunks[0]
        assert chunks[-1] == "data: [DONE]\n\n"
        mock_log_error.assert_called_once()
