---
name: xianxia-write-chapter-content
description: Draft or rewrite chapter prose using the canonical xianxia intrigue writing rules from others/.
kind: operation
tool_name: write_chapter_content
payload_contract: "{chapter_id? | chapter_number?, mode?: \"replace\"|\"append\", content}"
keywords:
  - 写章节
  - 改写章节
  - 正文
  - prose
references:
  - ../../../../../../others/章纲细纲设计提示词.txt
  - ../../../../../../others/写作提示词.txt
---
Use this skill when the user wants actual chapter prose.

- Generate the full candidate prose during planning.
- The prose must respect rank etiquette,利益驱动,内心独白, and cold strategic tone.
- Open on a concrete scene or action. End on unresolved pressure, revelation, or transition.
- Use `append` only for true continuation from the stored ending.
