---
name: update-character
description: Revise an existing character without losing established role, arc, or relationship logic.
kind: operation
tool_name: update_character
payload_contract: "{character_id? | character_name?, updates: {name?, role?, profile?, relationships?, arc_state?, notes?}}"
keywords:
  - 修改人物
  - 调整角色
  - 角色设定
  - character
references:
  - ../../references/writing_style.md
---
Use this skill when the user wants to revise an existing character.

- Resolve the target by `character_id` when available, otherwise by stable `character_name`.
- Only include fields that truly change.
- Preserve existing continuity unless the user explicitly requests a retcon.
- When changing notes, make the after-state usable for future drafting, not just descriptive.
