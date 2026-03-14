"""Draft Agent - creative writing assistant."""

from app.agents.base import AgentContext, AgentResult, BaseAgent


class DraftAgent(BaseAgent):
    """Agent for scene writing, content generation, and prose improvement."""

    def build_system_prompt(self, context: AgentContext) -> str:
        scene = context.context_data.get("current_scene", {})
        chapter = context.context_data.get("current_chapter", {})
        characters = context.context_data.get("characters", [])

        scene_text = ""
        if scene:
            scene_text = f"\n当前场景: 位置={scene.get('location', '未知')}, 内容片段: {(scene.get('content') or '')[:300]}"
        if chapter:
            scene_text += f"\n所属章节: 第{chapter.get('chapter_number', '?')}章 {chapter.get('title', '')}"

        chars_text = ""
        if characters:
            names = [c.get("name", "?") for c in characters[:5]]
            chars_text = f"\n相关人物: {', '.join(names)}"

        return f"""你是一位专业的小说写作助手，帮助作者撰写和润色小说正文。

上下文：{scene_text}{chars_text}

你的职责：
1. 根据大纲和设定撰写场景内容
2. 润色和改进现有文本
3. 保持文风一致性和人物声音
4. 当生成或修改内容时，用 JSON 格式包裹：
```json
{{"action": "content_gen", "content": "生成的正文内容", "word_count": 500, "notes": "写作说明"}}
```
或修改场景：
```json
{{"action": "scene_edit", "field": "content", "suggested_value": "修改后的内容", "reason": "修改原因"}}
```

请用中文回复。写作时注重文学性和可读性。"""

    async def run(self, context: AgentContext) -> AgentResult:
        response = await self._call_llm(context, temperature=0.8)

        suggestions = []
        parsed = self._parse_json_from_response(response)
        if parsed and parsed.get("action") in ("content_gen", "scene_edit"):
            suggestions.append({
                "type": parsed["action"],
                "target_type": "scene",
                "content": parsed,
            })

        return AgentResult(
            message=response,
            suggestions=suggestions,
            metadata={"agent": "draft"},
        )
