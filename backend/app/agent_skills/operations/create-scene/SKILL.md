---
name: create-scene
description: Create a scene inside a chapter with clear local objective, POV anchor, and situational pressure.
kind: operation
tool_name: create_scene
payload_contract: "{chapter_id? | chapter_number?, scene_order?, pov_character_id? | pov_character_name?, location?, content?, meta?}"
keywords:
  - 场景
  - 小节
  - scene
references:
  - ../../references/chapter_design.md
  - ../../references/writing_style.md
---
Use this skill when the user wants a new scene record.

- Tie the scene to a chapter explicitly or by chapter number.
- `scene_order` should fit the chapter flow.
- `location` should be concrete enough for staging and continuity.
- `content` is optional unless the user asks for drafted prose.
