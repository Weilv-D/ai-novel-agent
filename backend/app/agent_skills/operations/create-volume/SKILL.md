---
name: create-volume
description: Create a new volume that carries a mid-range structural objective and volume outline.
kind: operation
tool_name: create_volume
payload_contract: "{volume_number?, title?, outline?, notes?}"
keywords:
  - 卷
  - 卷细纲
  - 新建卷
references:
  - ../../references/outline_beats.md
  - ../../references/chapter_design.md
---
Use this skill when the user wants to add a new volume under the current project.

- A volume is a self-contained narrative unit with a strategic goal, causal chain, and closing transition.
- `outline` should summarize the volume goal, primary conflict, branch-line network, and volume-ending hook.
- Prefer explicit `volume_number` when the user gives one; otherwise let the service assign the next slot.
