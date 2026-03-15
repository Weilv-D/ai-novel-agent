---
name: xianxia-write-scene-content
description: Draft or rewrite scene prose with xianxia intrigue diction, hierarchy, and pressure.
kind: operation
tool_name: write_scene_content
payload_contract: "{scene_id? | chapter_id? | chapter_number?, scene_order?, mode?: \"replace\"|\"append\", content}"
keywords:
  - 写场景
  - 改写场景
  - 场景正文
references:
  - ../../../../../../others/章纲细纲设计提示词.txt
  - ../../../../../../others/写作提示词.txt
---
Use this skill when the user wants actual scene prose.

- Generate the final candidate prose in planning, not during execution.
- Keep one dominant objective, one dominant tension, and clear physical staging.
- Use the canonical tone: half-classical diction, restrained but sharp dialogue, and analytic inner monologue.
- End on a reveal, threat, reversal, or decision that pushes the next beat.
