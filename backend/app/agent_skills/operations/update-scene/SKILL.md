---
name: update-scene
description: Adjust an existing scene while preserving chapter flow, POV logic, and scene order.
kind: operation
tool_name: update_scene
payload_contract: "{scene_id? | chapter_id? | chapter_number?, scene_order?, updates: {scene_order?, pov_character_id? | pov_character_name?, location?, content?, meta?}}"
keywords:
  - 修改场景
  - 场景
  - scene
references:
  - ../../references/chapter_design.md
  - ../../references/writing_style.md
---
Use this skill when the user wants to revise a scene.

- Resolve the scene directly by `scene_id` when possible.
- If using chapter plus `scene_order`, ensure the reference is unambiguous.
- Only include changed fields in `updates`.
- Keep scene order and POV transitions coherent with neighboring scenes.
