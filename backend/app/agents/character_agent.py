"""Character Agent - character development assistant."""

from app.agents.base import AgentContext, AgentResult, BaseAgent


class CharacterAgent(BaseAgent):
    """Agent for character creation, development, and relationship management."""

    def build_system_prompt(self, context: AgentContext) -> str:
        characters = context.context_data.get("characters", [])
        chars_text = ""
        if characters:
            for c in characters:
                profile = c.get("profile", {}) or {}
                chars_text += f"\n- {c.get('name', '?')} ({c.get('role', '未知角色')}): {profile.get('description', '')[:150]}"

        return f"""你是一位专业的人物塑造助手，帮助作者创建和发展小说中的人物角色。

当前项目的人物：{chars_text or '暂无人物'}

你的职责：
1. 帮助作者创建立体的人物形象（性格、背景、动机、弧线等）
2. 分析人物关系和互动
3. 确保人物行为的一致性和成长轨迹
4. 当提出具体修改建议时，用 JSON 格式包裹：
```json
{{"action": "character_edit", "character_name": "人物名", "field": "要修改的字段", "suggested_value": "建议值", "reason": "修改原因"}}
```

请用中文回复。如果用户的问题不涉及人物，友好地引导回人物相关话题。"""

    async def run(self, context: AgentContext) -> AgentResult:
        response = await self._call_llm(context)

        suggestions = []
        parsed = self._parse_json_from_response(response)
        if parsed and parsed.get("action") == "character_edit":
            suggestions.append({
                "type": "character_edit",
                "target_type": "character",
                "content": parsed,
            })

        return AgentResult(
            message=response,
            suggestions=suggestions,
            metadata={"agent": "character"},
        )
