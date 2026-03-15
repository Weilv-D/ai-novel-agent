---
name: xianxia-update-chapter
description: Revise chapter metadata or structure while preserving sequence logic, beats, and branch-line linkage.
kind: operation
tool_name: update_chapter
payload_contract: "{chapter_id? | chapter_number?, updates: {chapter_number?, title?, outline?, content?, status?, notes?, volume_id?}}"
keywords:
  - 修改章节
  - 章纲
  - 细纲
references:
  - ../../../../../../others/大纲设计提示词.txt
  - ../../../../../../others/章纲细纲设计提示词.txt
---
Use this skill when revising an existing chapter.

- Keep the chapter aligned with beat progression and branch-line purpose.
- If `outline` changes, preserve因果链, stakes, and the chapter-ending hook.
- Only rewrite stored `content` when the user truly asks for text replacement.
