---
name: update-world-setting
description: Revise an existing setting while preserving category clarity and downstream continuity.
kind: operation
tool_name: update_world_setting
payload_contract: "{setting_id? | setting_name?, updates: {name?, category?, content?, meta?}}"
keywords:
  - 修改设定
  - 补充设定
  - 世界观
  - setting
references:
  - ../../references/outline_beats.md
---
Use this skill when the user wants to adjust an existing setting.

- Resolve the target by explicit id when available, otherwise by stable setting name.
- Treat `content` as canonical reference text. Rewrite it cleanly instead of appending scraps.
- Preserve continuity with characters, chapters, and scenes unless the user is intentionally retconning.
