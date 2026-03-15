---
name: create-world-setting
description: Create a reusable world-setting record that expands rules, factions, places, or artifacts.
kind: operation
tool_name: create_world_setting
payload_contract: "{name, category, content?, meta?}"
keywords:
  - 设定
  - 世界观
  - 门派
  - 宗门
  - 地域
  - world
  - setting
references:
  - ../../references/outline_beats.md
---
Use this skill when the user wants a new persistent setting entry.

- `name` should be a durable noun phrase.
- `category` should describe the slot clearly, such as faction, geography, rule, artifact, lineage, or history.
- `content` should explain usable story implications instead of encyclopedia filler.
- `meta` is optional and should only hold structured hints that matter later.
