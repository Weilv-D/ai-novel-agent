---
name: update-chapter
description: Revise chapter metadata, structure notes, or stored content while preserving sequencing logic.
kind: operation
tool_name: update_chapter
payload_contract: "{chapter_id? | chapter_number?, updates: {chapter_number?, title?, outline?, content?, status?, notes?, volume_id?}}"
keywords:
  - 修改章节
  - 章纲
  - chapter
references:
  - ../../references/outline_beats.md
  - ../../references/chapter_design.md
---
Use this skill when an existing chapter needs metadata or structural changes.

- Resolve the target by `chapter_id` when possible, otherwise by `chapter_number`.
- Keep chapter ordering stable unless the user explicitly requests renumbering.
- If changing `outline`, reflect cause, conflict, and payoff clearly enough for later drafting.
