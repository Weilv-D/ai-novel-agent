"""Outline Agent - story structure and chapter planning assistant."""

from app.agents.base import AgentContext, AgentResult, BaseAgent


class OutlineAgent(BaseAgent):
    """Agent for story outline generation and chapter planning."""

    def build_system_prompt(self, context: AgentContext) -> str:
        chapters = context.context_data.get("chapters", [])
        chapters_text = ""
        if chapters:
            for ch in chapters:
                chapters_text += f"\n- 第{ch.get('chapter_number', '?')}章 {ch.get('title', '无标题')}: {(ch.get('outline') or '')[:150]}"

        project = context.context_data.get("project", {})
        project_info = f"类型: {project.get('genre', '未知')}, 目标字数: {project.get('target_word_count', '未设定')}"

        return f"""你是一位专业的小说大纲策划助手，帮助作者构建和完善故事结构。

项目信息：{project_info}
当前章节：{chapters_text or '暂无章节'}

你的职责：
1. 帮助作者规划整体故事结构和节奏
2. 生成章节大纲和场景安排
3. 确保情节的逻辑性和吸引力
4. 当提出大纲或章节建议时，用 JSON 格式包裹：
```json
{{"action": "outline_gen", "chapter_number": 1, "title": "章节标题", "outline": "大纲内容", "reason": "设计理由"}}
```
或修改现有章节：
```json
{{"action": "chapter_edit", "chapter_number": 1, "field": "outline", "suggested_value": "新大纲", "reason": "修改原因"}}
```

请用中文回复。"""

    async def run(self, context: AgentContext) -> AgentResult:
        response = await self._call_llm(context)

        suggestions = []
        parsed = self._parse_json_from_response(response)
        if parsed and parsed.get("action") in ("outline_gen", "chapter_edit"):
            suggestions.append({
                "type": parsed["action"],
                "target_type": "chapter",
                "content": parsed,
            })

        return AgentResult(
            message=response,
            suggestions=suggestions,
            metadata={"agent": "outline"},
        )
