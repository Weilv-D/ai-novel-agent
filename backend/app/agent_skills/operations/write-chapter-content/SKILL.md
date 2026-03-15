---
name: write-chapter-content
description: Draft, rewrite, or extend full chapter prose in planning so execution can persist it unchanged.
kind: operation
tool_name: write_chapter_content
payload_contract: "{chapter_id? | chapter_number?, mode?: \"replace\"|\"append\", content}"
keywords:
  - 写章节
  - 改写章节
  - 续写章节
  - 正文
  - prose
  - chapter
references:
  - ../../references/writing_style.md
  - ../../references/chapter_design.md
---
Use this skill when the user wants actual chapter prose.

- Write the full candidate prose in `content` during planning.
- Respect existing chapter goals, character positions, and world rules.
- `replace` is for complete rewrites; `append` is for true continuation from the current ending.
- End on a meaningful beat, discovery, or pressure point instead of a flat stop.
