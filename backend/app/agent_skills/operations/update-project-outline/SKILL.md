---
name: update-project-outline
description: Revise the project-level story outline that governs long-range structure, themes, and progression.
kind: operation
tool_name: update_project_outline
payload_contract: "{updates: {story_outline}}"
keywords:
  - 项目大纲
  - 总纲
  - story outline
references:
  - ../../references/outline_beats.md
  - ../../references/chapter_design.md
---
Use this skill when the user wants to establish or revise the project-level story outline.

- `story_outline` should describe the long-range arc, stage goals, major causal turns, and strategic tension of the whole project.
- Keep it distinct from `summary`: this field is for working structure, not marketing copy.
- When revising, preserve stable canon unless the user clearly asks for a direction change.
