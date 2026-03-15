---
name: create-chapter
description: Create a new chapter scaffold with number, title, outline, and optional seed content.
kind: operation
tool_name: create_chapter
payload_contract: "{chapter_number?, title?, outline?, content?, status?, notes?, volume_id?}"
keywords:
  - 章节
  - 新章
  - 章纲
  - chapter
references:
  - ../../references/outline_beats.md
  - ../../references/chapter_design.md
---
Use this skill when the user wants a new chapter record.

- Prefer a concrete `chapter_number` if the user gives one.
- `title` should be short and carry narrative pressure.
- `outline` should describe conflict, turning point, and consequence, not just a topic label.
- Only place prose in `content` if the user explicitly asks for drafting.
