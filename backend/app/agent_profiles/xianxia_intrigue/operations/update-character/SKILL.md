---
name: xianxia-update-character
description: Revise an existing character while preserving identity hierarchy, strategic motive, and continuity.
kind: operation
tool_name: update_character
payload_contract: "{character_id? | character_name?, updates: {name?, role?, profile?, relationships?, arc_state?, notes?}}"
keywords:
  - 修改人物
  - 角色设定
  - 人物弧光
references:
  - ../../../../../../others/写作提示词.txt
---
Use this skill when revising a persistent character.

- Preserve established rank,称谓,利益关系, and arc logic unless the user explicitly requests a retcon.
- Only include fields that truly change.
- If updating `notes`, keep them actionable for later drafting and continuity review.
