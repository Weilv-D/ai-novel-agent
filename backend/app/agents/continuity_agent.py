"""Continuity Agent - consistency checking assistant."""

from app.agents.base import AgentContext, AgentResult, BaseAgent


class ContinuityAgent(BaseAgent):
    """Agent for checking narrative consistency and continuity errors."""

    def build_system_prompt(self, context: AgentContext) -> str:
        characters = context.context_data.get("characters", [])
        world_settings = context.context_data.get("world_settings", [])
        chapters = context.context_data.get("chapters", [])
        memories = context.context_data.get("memories", [])

        ctx_parts = []
        if characters:
            chars = [f"{c.get('name', '?')} ({c.get('role', '')})" for c in characters]
            ctx_parts.append(f"人物: {', '.join(chars)}")
        if world_settings:
            settings = [f"{ws.get('name', '?')}" for ws in world_settings[:10]]
            ctx_parts.append(f"世界设定: {', '.join(settings)}")
        if chapters:
            chs = [f"第{ch.get('chapter_number', '?')}章" for ch in chapters]
            ctx_parts.append(f"章节: {', '.join(chs)}")
        if memories:
            facts = [m.get("content", "")[:80] for m in memories[:5]]
            ctx_parts.append(f"已知事实: {'; '.join(facts)}")

        context_text = "\n".join(ctx_parts) if ctx_parts else "暂无上下文"

        return f"""你是一位专业的小说连续性检查助手，负责发现和修复叙事中的不一致问题。

项目上下文：
{context_text}

你的职责：
1. 检查人物行为与设定是否一致
2. 发现时间线矛盾和情节漏洞
3. 核实世界观规则是否被违反
4. 当发现问题并提出修复建议时，用 JSON 格式包裹：
```json
{{"action": "continuity_fix", "issue": "问题描述", "target_type": "chapter/character/scene", "target_hint": "目标标识", "suggested_fix": "修复建议", "severity": "high/medium/low"}}
```

请用中文回复。检查时要严谨但不吹毛求疵。"""

    async def run(self, context: AgentContext) -> AgentResult:
        response = await self._call_llm(context, temperature=0.3)

        suggestions = []
        parsed = self._parse_json_from_response(response)
        if parsed and parsed.get("action") == "continuity_fix":
            target_type = parsed.get("target_type", "chapter")
            if target_type not in ("character", "world_setting", "chapter", "scene"):
                target_type = "chapter"
            suggestions.append({
                "type": "continuity_fix",
                "target_type": target_type,
                "content": parsed,
            })

        return AgentResult(
            message=response,
            suggestions=suggestions,
            metadata={"agent": "continuity"},
        )
