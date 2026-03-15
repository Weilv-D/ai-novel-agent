---
name: xianxia-update-scene
description: Revise a scene while preserving chapter energy, POV continuity, and strategic causality.
kind: operation
tool_name: update_scene
payload_contract: "{scene_id? | chapter_id? | chapter_number?, scene_order?, updates: {scene_order?, pov_character_id? | pov_character_name?, location?, content?, meta?}}"
keywords:
  - 修改场景
  - 场景
  - scene
references:
  - ../../../../../../others/章纲细纲设计提示词.txt
  - ../../../../../../others/写作提示词.txt
---
Use this skill when revising an existing scene.

- Preserve the scene's role in the chapter-level beat flow unless the user requests a structural rewrite.
- Keep scene order, POV, and information release coherent with neighboring scenes.
- Only include changed fields in `updates`.
