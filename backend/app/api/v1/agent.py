"""Agent workflow API routes."""

import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import orchestrator
from app.api.deps import get_db
from app.schemas.agent import (
    AgentCapabilityRegistryResponse,
    AgentChatRequest,
    AgentChatResponse,
    AgentProfileResponse,
    AgentRiskPolicyRegistryResponse,
    AgentRunActionResponse,
    AgentRunResponse,
    AgentSkillCatalogResponse,
    AgentThreadCreateRequest,
    AgentThreadMessageRequest,
    AgentThreadMessageResponse,
    AgentThreadResponse,
    AgentThreadStateResponse,
    AutoSummarizeRequest,
    AutoSummarizeResponse,
    ContinuityCheckRequest,
    InlineEditRequest,
)
from app.services.agent_workflow import agent_workflow_service
from app.services.llm import llm_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


def _chunk_text(text: str, *, size: int = 120) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


INLINE_EDIT_OPERATIONS = {
    "rewrite": "在不改变事实、人物关系和核心情节的前提下改写这段文字，优化节奏、措辞和画面感。",
    "expand": "在保持事实和风格一致的前提下扩写这段文字，补足动作、感官和情绪细节。",
    "condense": "压缩这段文字，保留关键动作、信息和情绪，删去冗余表达。",
    "change_pov": "把这段文字改写成另一种更明确的叙述视角；若上下文提供 target_pov，请优先按该视角处理。",
}


def _build_inline_edit_messages(req: InlineEditRequest) -> list[dict[str, str]]:
    context_block = json.dumps(req.context, ensure_ascii=False, indent=2) if req.context else "无"
    return [
        {
            "role": "system",
            "content": (
                "你是中文长篇小说编辑。请只返回修改后的正文，不要解释，不要列点，不要加标题，不要加引号。"
                "保持原文语言和人名地名不变，除非操作本身要求调整视角。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"操作要求：{INLINE_EDIT_OPERATIONS[req.operation]}\n\n"
                f"上下文：\n{context_block}\n\n"
                f"待处理文本：\n{req.text}"
            ),
        },
    ]


@router.post("/threads", response_model=AgentThreadResponse)
async def create_or_get_thread(
    *,
    db: AsyncSession = Depends(get_db),
    req: AgentThreadCreateRequest,
) -> AgentThreadResponse:
    """Create or fetch the default project-scoped agent thread."""
    return await agent_workflow_service.get_or_create_thread_response(db, project_id=req.project_id)


@router.get("/threads/{thread_id}", response_model=AgentThreadStateResponse)
async def get_thread(
    *,
    db: AsyncSession = Depends(get_db),
    thread_id: UUID,
) -> AgentThreadStateResponse:
    """Fetch thread messages and recent runs for the Agent Workspace."""
    return await agent_workflow_service.get_thread_state_response(db, thread_id=thread_id)


@router.get("/profiles", response_model=list[AgentProfileResponse])
async def list_agent_profiles() -> list[AgentProfileResponse]:
    """List available project-level agent profiles."""
    return await agent_workflow_service.get_profile_catalog_response()


@router.get("/capabilities", response_model=AgentCapabilityRegistryResponse)
async def get_agent_capabilities() -> AgentCapabilityRegistryResponse:
    """Inspect the stable capability registry used by the workflow."""
    return await agent_workflow_service.get_capability_registry_response()


@router.get("/risk-policies", response_model=AgentRiskPolicyRegistryResponse)
async def get_agent_risk_policies(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID | None = None,
    profile_id: str | None = None,
) -> AgentRiskPolicyRegistryResponse:
    """Inspect the stable risk policy registry used by the workflow."""
    return await agent_workflow_service.get_risk_policy_registry_response(
        db,
        project_id=project_id,
        profile_id=profile_id,
    )


@router.get("/skills", response_model=AgentSkillCatalogResponse)
async def get_agent_skills(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID | None = None,
) -> AgentSkillCatalogResponse:
    """Inspect the active planner and operation skills."""
    return await agent_workflow_service.get_skill_catalog_response(db, project_id=project_id)


@router.post("/threads/{thread_id}/messages", response_model=AgentThreadMessageResponse)
async def create_thread_message(
    *,
    db: AsyncSession = Depends(get_db),
    thread_id: UUID,
    req: AgentThreadMessageRequest,
) -> AgentThreadMessageResponse | StreamingResponse:
    """Send a message into an agent thread and receive a planned run."""
    if not req.stream:
        response = await agent_workflow_service.create_planned_run(
            db,
            thread_id=thread_id,
            content=req.content,
            context=req.context,
        )
        return response

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in agent_workflow_service.stream_planned_run(
                db,
                thread_id=thread_id,
                content=req.content,
                context=req.context,
            ):
                payload = event.model_dump(mode="json")
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Stream error in thread %s: %s", thread_id, e)
            error_payload = {
                "type": "error",
                "message": "An error occurred during processing",
                "detail": {},
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_run(
    *,
    db: AsyncSession = Depends(get_db),
    run_id: UUID,
) -> AgentRunResponse:
    """Fetch a single run with its operation previews/results."""
    return await agent_workflow_service.get_run_response(db, run_id=run_id)


@router.post("/runs/{run_id}/confirm", response_model=AgentRunActionResponse)
async def confirm_run(
    *,
    db: AsyncSession = Depends(get_db),
    run_id: UUID,
) -> AgentRunActionResponse:
    """Confirm and execute a planned run."""
    return await agent_workflow_service.confirm_run_response(db, run_id=run_id)


@router.post("/runs/{run_id}/confirm-high-risk", response_model=AgentRunActionResponse)
async def confirm_high_risk_run(
    *,
    db: AsyncSession = Depends(get_db),
    run_id: UUID,
) -> AgentRunActionResponse:
    """Execute a run after the secondary confirmation for high-risk writes."""
    return await agent_workflow_service.confirm_high_risk_run_response(db, run_id=run_id)


@router.post("/runs/{run_id}/cancel", response_model=AgentRunActionResponse)
async def cancel_run(
    *,
    db: AsyncSession = Depends(get_db),
    run_id: UUID,
) -> AgentRunActionResponse:
    """Cancel a run that has not been executed yet."""
    return await agent_workflow_service.cancel_run_response(db, run_id=run_id)


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    *,
    db: AsyncSession = Depends(get_db),
    req: AgentChatRequest,
) -> AgentChatResponse:
    """Legacy chat endpoint kept for auxiliary pages."""
    result = await orchestrator.chat(
        db,
        project_id=str(req.project_id),
        user_message=req.message,
        history=req.history,
        extra_context=req.context,
    )
    return AgentChatResponse(
        message=result.message,
        suggestions=result.suggestions,
        metadata=result.metadata,
    )


@router.post("/chat/stream")
async def agent_chat_stream(
    *,
    db: AsyncSession = Depends(get_db),
    req: AgentChatRequest,
) -> StreamingResponse:
    """Legacy streaming chat endpoint kept for auxiliary pages."""

    async def event_generator() -> AsyncIterator[str]:
        async for chunk in orchestrator.chat_stream(
            db,
            project_id=str(req.project_id),
            user_message=req.message,
            history=req.history,
            extra_context=req.context,
        ):
            data = json.dumps({"content": chunk}, ensure_ascii=False)
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/auto-summarize", response_model=AutoSummarizeResponse)
async def auto_summarize(
    *,
    db: AsyncSession = Depends(get_db),
    req: AutoSummarizeRequest,
) -> AutoSummarizeResponse:
    """Legacy auto-summarize endpoint."""
    memories = await orchestrator.auto_summarize(
        db,
        project_id=str(req.project_id),
        chapter_id=str(req.chapter_id),
        content=req.content,
    )
    return AutoSummarizeResponse(memories=memories, count=len(memories))


@router.post("/continuity-check", response_model=AgentChatResponse)
async def continuity_check(
    *,
    db: AsyncSession = Depends(get_db),
    req: ContinuityCheckRequest,
) -> AgentChatResponse:
    """Legacy continuity check endpoint."""
    result = await orchestrator.continuity_check(
        db,
        project_id=str(req.project_id),
        content=req.content,
    )
    return AgentChatResponse(
        message=result.message,
        suggestions=result.suggestions,
        metadata=result.metadata,
    )


@router.post("/inline-edit")
async def inline_edit(
    *,
    req: InlineEditRequest,
) -> StreamingResponse:
    """Stream an inline rewrite for a selected text fragment."""

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in llm_service.generate_stream(
                _build_inline_edit_messages(req),
                temperature=0.6,
            ):
                data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("Inline edit stream error: %s", exc)
            error_payload = {"type": "error", "message": "Inline edit failed"}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
