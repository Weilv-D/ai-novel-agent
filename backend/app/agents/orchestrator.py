"""WritingOrchestrator - routes user requests to specialized agents."""

import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.character_agent import CharacterAgent
from app.agents.continuity_agent import ContinuityAgent
from app.agents.draft_agent import DraftAgent
from app.agents.lore_agent import LoreAgent
from app.agents.outline_agent import OutlineAgent
from app.schemas.suggestion import SuggestionCreate
from app.services.chapter import chapter_service, volume_service
from app.services.character import character_service
from app.services.llm import LLMService, llm_service
from app.services.memory import memory_service
from app.services.suggestion import suggestion_service
from app.services.world_setting import world_setting_service

logger = logging.getLogger(__name__)

AGENT_MAP: dict[str, type[BaseAgent]] = {
    "lore": LoreAgent,
    "character": CharacterAgent,
    "outline": OutlineAgent,
    "draft": DraftAgent,
    "continuity": ContinuityAgent,
}

CLASSIFY_PROMPT = """你是一个意图分类器。根据用户消息，判断应该由哪个 Agent 处理。

可选 Agent：
- lore: 世界观相关（魔法体系、地理、历史、组织、科技、文化等设定）
- character: 人物相关（创建角色、性格分析、人物关系、角色弧线）
- outline: 大纲相关（故事结构、章节规划、情节安排）
- draft: 写作相关（撰写正文、场景描写、润色文本、内容生成）
- continuity: 连续性检查（一致性检查、情节漏洞、时间线矛盾）

只回复一个词（lore/character/outline/draft/continuity），不要其他内容。

用户消息：{message}"""


class WritingOrchestrator:
    """Orchestrates user requests by classifying intent and delegating to agents."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self.llm = llm or llm_service
        self._agents: dict[str, BaseAgent] = {}

    def _get_agent(self, agent_type: str) -> BaseAgent:
        if agent_type not in self._agents:
            agent_cls = AGENT_MAP.get(agent_type)
            if not agent_cls:
                agent_cls = DraftAgent  # default fallback
            self._agents[agent_type] = agent_cls(llm=self.llm)
        return self._agents[agent_type]

    async def classify(self, message: str) -> str:
        """Classify user message to determine which agent to use."""
        prompt = CLASSIFY_PROMPT.format(message=message)
        result = await self.llm.generate(
            [{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.0,
        )
        agent_type = result["content"].strip().lower()
        if agent_type not in AGENT_MAP:
            logger.warning("Unknown agent type '%s', falling back to draft", agent_type)
            agent_type = "draft"
        return agent_type

    async def load_context(
        self, db: AsyncSession, project_id: str, extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load project context from database."""
        pid = project_id
        context_data: dict[str, Any] = {}

        try:
            from app.services.project import project_service
            project = await project_service.get(db, id=pid)
            if project:
                context_data["project"] = {
                    "id": str(project.id),
                    "name": project.name,
                    "genre": project.genre,
                    "target_word_count": project.target_word_count,
                    "summary": project.summary,
                    "story_outline": project.story_outline,
                }
        except Exception:
            pass

        try:
            characters = await character_service.get_by_project(db, project_id=pid, limit=20)
            context_data["characters"] = [
                {"id": str(c.id), "name": c.name, "role": c.role, "profile": c.profile}
                for c in characters
            ]
        except Exception:
            context_data["characters"] = []

        try:
            settings = await world_setting_service.get_by_project(db, project_id=pid, limit=20)
            context_data["world_settings"] = [
                {
                    "id": str(ws.id),
                    "category": ws.category,
                    "name": ws.name,
                    "content": (ws.content or "")[:300],
                }
                for ws in settings
            ]
        except Exception:
            context_data["world_settings"] = []

        try:
            volumes = await volume_service.get_by_project(db, project_id=pid, limit=20)
            context_data["volumes"] = [
                {
                    "id": str(volume.id),
                    "volume_number": volume.volume_number,
                    "title": volume.title,
                    "outline": (volume.outline or "")[:300],
                }
                for volume in volumes
            ]
        except Exception:
            context_data["volumes"] = []

        try:
            chapters = await chapter_service.get_by_project(db, project_id=pid, limit=50)
            context_data["chapters"] = [
                {
                    "id": str(ch.id),
                    "volume_id": str(ch.volume_id) if ch.volume_id is not None else None,
                    "chapter_number": ch.chapter_number,
                    "title": ch.title,
                    "outline": ch.outline,
                    "status": ch.status,
                }
                for ch in chapters
            ]
        except Exception:
            context_data["chapters"] = []

        try:
            memories = await memory_service.get_by_project(db, project_id=pid, limit=10)
            context_data["memories"] = [
                {"content": m.content, "memory_type": m.memory_type}
                for m in memories
            ]
        except Exception:
            context_data["memories"] = []

        if extra:
            context_data.update(extra)

        return context_data

    async def chat(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Process a chat message: classify, load context, run agent, save suggestions."""
        agent_type = await self.classify(user_message)
        context_data = await self.load_context(db, project_id, extra_context)

        ctx = AgentContext(
            project_id=project_id,
            user_message=user_message,
            history=history or [],
            context_data=context_data,
        )

        agent = self._get_agent(agent_type)
        result = await agent.run(ctx)
        result.metadata["agent_type"] = agent_type

        # Save suggestions to database
        for sug in result.suggestions:
            target_id = self._resolve_target_id(sug, context_data)
            try:
                await suggestion_service.create_with_project(
                    db,
                    obj_in=SuggestionCreate(
                        project_id=uuid.UUID(project_id),
                        target_type=sug["target_type"],
                        target_id=target_id,
                        type=sug["type"],
                        content=sug["content"],
                    ),
                    project_id=uuid.UUID(project_id),
                )
            except Exception as e:
                logger.error("Failed to save suggestion: %s", e)

        return result

    async def chat_stream(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Process a chat message with streaming response."""
        agent_type = await self.classify(user_message)
        context_data = await self.load_context(db, project_id, extra_context)

        ctx = AgentContext(
            project_id=project_id,
            user_message=user_message,
            history=history or [],
            context_data=context_data,
        )

        agent = self._get_agent(agent_type)

        # Stream the response
        full_response = ""
        async for chunk in agent._call_llm_stream(ctx):
            full_response += chunk
            yield chunk

        # After streaming completes, check for suggestions
        parsed = agent._parse_json_from_response(full_response)
        if parsed and parsed.get("action"):
            sug_type = parsed["action"]
            target_type_map = {
                "world_edit": "world_setting",
                "character_edit": "character",
                "outline_gen": parsed.get("target_type", "chapter"),
                "chapter_edit": "chapter",
                "content_gen": "scene",
                "scene_edit": "scene",
                "continuity_fix": parsed.get("target_type", "chapter"),
            }
            target_type = target_type_map.get(sug_type, "chapter")
            target_id = self._resolve_target_id(
                {"target_type": target_type, "content": parsed}, context_data
            )
            try:
                sug_obj = await suggestion_service.create_with_project(
                    db,
                    obj_in=SuggestionCreate(
                        project_id=uuid.UUID(project_id),
                        target_type=target_type,
                        target_id=target_id,
                        type=sug_type,
                        content=parsed,
                    ),
                    project_id=uuid.UUID(project_id),
                )
                # Yield a special event with suggestion ID
                yield f"\n[SUGGESTION:{sug_obj.id}]"
            except Exception as e:
                logger.error("Failed to save suggestion from stream: %s", e)

    async def auto_summarize(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        chapter_id: str,
        content: str,
    ) -> list[dict[str, Any]]:
        """Auto-summarize chapter content into memory facts."""

        prompt = f"""分析以下章节内容，提取关键事实和情节要点。
以 JSON 数组格式返回，每个元素包含：
- "memory_type": "episode"（事件）或 "fact"（事实）或 "semantic"（设定/规则）
- "content": 事实内容（简洁明确）

内容：
{content[:3000]}

只返回 JSON 数组，不要其他内容。"""

        result = await self.llm.generate(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        import json
        import re
        text = result["content"]
        # Extract JSON array
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []

        try:
            facts = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

        created = []
        for fact in facts:
            if not isinstance(fact, dict) or "content" not in fact:
                continue
            memory_type = fact.get("memory_type", "fact")
            if memory_type not in ("episode", "semantic", "fact"):
                memory_type = "fact"

            try:
                # Generate embedding for the fact
                embedding = await self.llm.embed_single(fact["content"])
                from app.models.memory import Memory
                mem = Memory(
                    project_id=uuid.UUID(project_id),
                    memory_type=memory_type,
                    content=fact["content"],
                    embedding=embedding,
                    meta={"source_chapter_id": chapter_id},
                )
                db.add(mem)
                await db.flush()
                await db.refresh(mem)
                created.append({
                    "id": str(mem.id),
                    "memory_type": memory_type,
                    "content": fact["content"],
                })
            except Exception as e:
                logger.error("Failed to create memory: %s", e)

        return created

    async def continuity_check(
        self,
        db: AsyncSession,
        *,
        project_id: str,
        content: str,
    ) -> AgentResult:
        """Run a continuity check on the given content."""
        context_data = await self.load_context(db, project_id)
        ctx = AgentContext(
            project_id=project_id,
            user_message=f"请检查以下内容的连续性和一致性问题：\n\n{content[:3000]}",
            context_data=context_data,
        )
        agent = self._get_agent("continuity")
        return await agent.run(ctx)

    def _resolve_target_id(
        self, suggestion: dict[str, Any], context_data: dict[str, Any]
    ) -> uuid.UUID:
        """Resolve target_id for a suggestion, using context data to find matching entities."""
        target_type = suggestion.get("target_type", "")
        content = suggestion.get("content", {})

        # Try to find matching entity by name/number from context
        if target_type == "character" and content.get("character_name"):
            for c in context_data.get("characters", []):
                if c.get("name") == content["character_name"]:
                    return uuid.UUID(c["id"])

        if target_type == "world_setting" and content.get("target_name"):
            for ws in context_data.get("world_settings", []):
                if ws.get("name") == content["target_name"]:
                    return uuid.UUID(ws["id"])

        if target_type == "chapter" and content.get("chapter_number"):
            for ch in context_data.get("chapters", []):
                if ch.get("chapter_number") == content["chapter_number"]:
                    return uuid.UUID(ch["id"])

        if target_type == "project":
            project = context_data.get("project", {})
            if project.get("id"):
                return uuid.UUID(project["id"])

        if target_type == "volume":
            if content.get("volume_number"):
                for volume in context_data.get("volumes", []):
                    if volume.get("volume_number") == content["volume_number"]:
                        return uuid.UUID(volume["id"])
            if content.get("volume_title"):
                for volume in context_data.get("volumes", []):
                    if volume.get("title") == content["volume_title"]:
                        return uuid.UUID(volume["id"])

        # Fallback: use first entity of matching type, or generate a placeholder
        type_to_list = {
            "project": "project",
            "character": "characters",
            "world_setting": "world_settings",
            "volume": "volumes",
            "chapter": "chapters",
        }
        list_key = type_to_list.get(target_type)
        if list_key == "project" and context_data.get("project", {}).get("id"):
            return uuid.UUID(context_data["project"]["id"])
        if list_key and list_key != "project" and context_data.get(list_key):
            return uuid.UUID(context_data[list_key][0]["id"])

        # Final fallback: generate a new UUID (suggestion will reference a non-existent entity)
        return uuid.uuid4()


# Singleton
orchestrator = WritingOrchestrator()
