---
name: update-volume
description: Revise an existing volume outline, numbering, or notes while keeping project hierarchy coherent.
kind: operation
tool_name: update_volume
payload_contract: "{volume_id? | volume_number?, updates: {volume_number?, title?, outline?, notes?}}"
keywords:
  - 修改卷
  - 卷细纲
  - volume
references:
  - ../../references/outline_beats.md
  - ../../references/chapter_design.md
---
Use this skill when a volume needs structural revision.

- Resolve by `volume_id` when available, otherwise by `volume_number`.
- Keep `outline` focused on volume-level progression, not per-scene beats.
- If renumbering, maintain a clean sequence and avoid collisions with sibling volumes.
