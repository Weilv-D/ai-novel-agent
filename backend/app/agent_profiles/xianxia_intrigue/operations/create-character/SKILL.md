---
name: xianxia-create-character
description: Create a new character whose function, identity, and motivation match the xianxia intrigue profile.
kind: operation
tool_name: create_character
payload_contract: "{name, role?, profile?, relationships?, arc_state?, notes?}"
keywords:
  - 人物
  - 角色
  - 主角
  - 配角
  - 反派
references:
  - ../../../../../../others/写作提示词.txt
---
Use this skill when the user wants a persistent character entry.

- `role` must reflect story function and power position, not only occupation.
- `profile` should encode identity,利益驱动, status etiquette, and present tension.
- `relationships` should reveal faction alignment, dependency, suspicion, or leverage when available.
- `notes` should preserve reveal hooks, debut pressure, and strategy value for later writing.
