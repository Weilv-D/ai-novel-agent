"""Agent API routes for AI-assisted writing."""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import orchestrator
from app.api.deps import get_db
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AutoSummarizeRequest,
    AutoSummarizeResponse,
    ContinuityCheckRequest,
)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    *,
    db: AsyncSession = Depends(get_db),
    req: AgentChatRequest,
) -> AgentChatResponse:
    """Send a message to the AI writing assistant."""
    result = await orchestrator.chat(
        db,
        project_id=req.project_id,
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
    """Send a message to the AI writing assistant with SSE streaming."""

    async def event_generator():
        async for chunk in orchestrator.chat_stream(
            db,
            project_id=req.project_id,
            user_message=req.message,
            history=req.history,
            extra_context=req.context,
        ):
            # SSE format
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
    """Auto-summarize chapter content into memory facts."""
    memories = await orchestrator.auto_summarize(
        db,
        project_id=req.project_id,
        chapter_id=req.chapter_id,
        content=req.content,
    )
    return AutoSummarizeResponse(memories=memories, count=len(memories))


@router.post("/continuity-check", response_model=AgentChatResponse)
async def continuity_check(
    *,
    db: AsyncSession = Depends(get_db),
    req: ContinuityCheckRequest,
) -> AgentChatResponse:
    """Run a continuity check on content."""
    result = await orchestrator.continuity_check(
        db,
        project_id=req.project_id,
        content=req.content,
    )
    return AgentChatResponse(
        message=result.message,
        suggestions=result.suggestions,
        metadata=result.metadata,
    )
