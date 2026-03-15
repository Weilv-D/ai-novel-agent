---
name: create-character
description: Create a new named character with clear story function, motivation, and debut value.
kind: operation
tool_name: create_character
payload_contract: "{name, role?, profile?, relationships?, arc_state?, notes?}"
keywords:
  - 人物
  - 角色
  - 主角
  - 配角
  - 反派
  - character
references:
  - ../../references/writing_style.md
---
Use this skill when the user wants a new persisted character.

- `name` must be explicit and stable.
- `role` should capture story function, not only occupation.
- `profile` should summarize public persona, core drive, and present tension.
- `relationships` should list concrete ties when they already exist.
- `notes` can hold reveal hooks, debut chapter hints, or constraints the writer will care about later.
