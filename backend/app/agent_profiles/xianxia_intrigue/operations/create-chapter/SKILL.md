---
name: xianxia-create-chapter
description: Create a chapter scaffold that follows beat rhythm, branch-line placement, and xianxia intrigue pacing.
kind: operation
tool_name: create_chapter
payload_contract: "{chapter_number?, title?, outline?, content?, status?, notes?, volume_id?}"
keywords:
  - 章节
  - 章纲
  - 新章
  - 卷内支线
references:
  - ../../../../../../others/大纲设计提示词.txt
  - ../../../../../../others/章纲细纲设计提示词.txt
  - ../../../../../../others/写作提示词.txt
---
Use this skill when creating a new chapter record.

- The chapter must have a clear structural function:推进情节、揭示信息、展现代价、或深化主题。
- `outline` should encode hook, development, and closing pressure; avoid empty topic labels.
- If prose is requested, keep the opening concrete and the ending on an unresolved question, discovery, or turn.
