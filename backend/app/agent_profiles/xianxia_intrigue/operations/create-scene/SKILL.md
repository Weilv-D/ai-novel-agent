---
name: xianxia-create-scene
description: Create a scene with local objective, POV control, and branch-aware narrative pressure.
kind: operation
tool_name: create_scene
payload_contract: "{chapter_id? | chapter_number?, scene_order?, pov_character_id? | pov_character_name?, location?, content?, meta?}"
keywords:
  - 场景
  - 小节
  - scene
references:
  - ../../../../../../others/章纲细纲设计提示词.txt
  - ../../../../../../others/写作提示词.txt
---
Use this skill when the user wants a new scene record.

- Each scene should serve one local objective and one major tension.
- Keep POV explicit and compatible with the chapter's information design.
- If prose is included, preserve xianxia tone, concrete staging, and exit momentum.
