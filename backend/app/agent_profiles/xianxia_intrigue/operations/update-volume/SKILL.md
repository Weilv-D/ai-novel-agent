---
name: xianxia-update-volume
description: Revise a volume outline while preserving causal chain, branch-line linkage, and xianxia intrigue structure.
kind: operation
tool_name: update_volume
payload_contract: "{volume_id? | volume_number?, updates: {volume_number?, title?, outline?, notes?}}"
keywords:
  - 修改卷
  - 卷细纲
  - 卷内支线
references:
  - ../../../../../../others/大纲设计提示词.txt
  - ../../../../../../others/章纲细纲设计提示词.txt
---
Use this skill when revising an existing volume.

- Maintain卷目标、因果链、支线勾连、 and the volume-ending momentum.
- Keep the volume outline concrete enough that chapter creation can expand it directly into章纲.
- Only renumber the volume when the user explicitly asks for structural resequencing.
