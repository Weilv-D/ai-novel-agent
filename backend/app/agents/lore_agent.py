"""Lore Agent - world-building assistant."""

from app.agents.base import AgentContext, AgentResult, BaseAgent


class LoreAgent(BaseAgent):
    """Agent for world-building: magic systems, geography, history, etc."""

    def build_system_prompt(self, context: AgentContext) -> str:
        world_settings = context.context_data.get("world_settings", [])
        settings_text = ""
        if world_settings:
            for ws in world_settings:
                settings_text += f"\n- [{ws.get('category', '')}] {ws.get('name', '')}: {ws.get('content', '')[:200]}"

        return f"""你是一位专业的世界观构建助手，帮助作者设计和完善小说的世界观设定。

当前项目的世界观设定：{settings_text or '暂无设定'}

你的职责：
1. 帮助作者构思和完善世界观元素（魔法体系、地理、历史、组织、科技、文化、宗教、经济、规则等）
2. 检查世界观设定的内在一致性
3. 提出扩展和深化建议
4. 当提出具体修改建议时，用 JSON 格式包裹，格式如下：
```json
{{"action": "world_edit", "target_name": "设定名称", "category": "分类", "suggested_content": "建议内容", "reason": "修改原因"}}
```

请用中文回复。如果用户的问题不涉及世界观，友好地引导回世界观相关话题。"""

    async def run(self, context: AgentContext) -> AgentResult:
        response = await self._call_llm(context)

        suggestions = []
        parsed = self._parse_json_from_response(response)
        if parsed and parsed.get("action") == "world_edit":
            suggestions.append({
                "type": "world_edit",
                "target_type": "world_setting",
                "content": parsed,
            })

        return AgentResult(
            message=response,
            suggestions=suggestions,
            metadata={"agent": "lore"},
        )
