---
name: xianxia-update-world-setting
description: Revise an existing setting while preserving causal coherence, strategic value, and xianxia terminology.
kind: operation
tool_name: update_world_setting
payload_contract: "{setting_id? | setting_name?, updates: {name?, category?, content?, meta?}}"
keywords:
  - 修改设定
  - 世界观
  - 势力
references:
  - ../../../../../../others/大纲设计提示词.txt
  - ../../../../../../others/写作提示词.txt
---
Use this skill when adjusting canonical setting text.

- Rewrite `content` cleanly as canonical reference text, not fragmented append-only notes.
- Preserve faction logic, rule cost, and information asymmetry across the project.
- Treat setting changes as downstream continuity-sensitive edits.
