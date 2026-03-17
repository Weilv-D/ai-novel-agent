# API Reference

最后更新：2026-03-17
来源：本地 `app.openapi()` 结果（`66` paths / `92` schemas）

## 1. 基础信息

- Base URL：`http://localhost:8000/api/v1`
- OpenAPI：`/openapi.json`
- Swagger UI：`/docs`
- 默认鉴权头：`X-API-Key: <ADMIN_API_KEY>`
- 内容类型：JSON 接口默认 `Content-Type: application/json`

除 `GET /api/v1/health` 外，业务接口在配置 `ADMIN_API_KEY` 后均要求鉴权。

## 2. 当前资源分组

### Health / Root

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/` | 根信息 |
| `GET` | `/api/v1/health` | 健康检查 |

### Projects / Export / Package / Timeline

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/projects` | 项目列表 |
| `POST` | `/api/v1/projects` | 创建项目 |
| `GET` | `/api/v1/projects/{project_id}` | 项目详情 |
| `PATCH` | `/api/v1/projects/{project_id}` | 更新项目 |
| `DELETE` | `/api/v1/projects/{project_id}` | 删除项目 |
| `GET` | `/api/v1/projects/{project_id}/export` | TXT / Markdown / DOCX 导出 |
| `GET` | `/api/v1/projects/{project_id}/package` | 项目包导出 |
| `POST` | `/api/v1/projects/import` | 项目包导入 |
| `GET` | `/api/v1/projects/{project_id}/timeline` | 时间线聚合 |

### Characters

| Method | Path | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/characters` | 创建人物 |
| `GET` | `/api/v1/characters/project/{project_id}` | 项目人物列表 |
| `GET` | `/api/v1/characters/{character_id}` | 人物详情 |
| `PATCH` | `/api/v1/characters/{character_id}` | 更新人物 |
| `DELETE` | `/api/v1/characters/{character_id}` | 删除人物 |

### World Settings

| Method | Path | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/world-settings` | 创建设定 |
| `GET` | `/api/v1/world-settings/project/{project_id}` | 项目设定列表 |
| `GET` | `/api/v1/world-settings/project/{project_id}/category/{category}` | 分类列表 |
| `GET` | `/api/v1/world-settings/{setting_id}` | 设定详情 |
| `PATCH` | `/api/v1/world-settings/{setting_id}` | 更新设定 |
| `DELETE` | `/api/v1/world-settings/{setting_id}` | 删除设定 |

### Volumes / Chapters / Scenes

| Method | Path | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/volumes` | 创建卷 |
| `GET` | `/api/v1/volumes/project/{project_id}` | 项目卷列表 |
| `GET` | `/api/v1/volumes/{volume_id}` | 卷详情 |
| `PATCH` | `/api/v1/volumes/{volume_id}` | 更新卷 |
| `DELETE` | `/api/v1/volumes/{volume_id}` | 删除卷 |
| `POST` | `/api/v1/chapters` | 创建章节 |
| `GET` | `/api/v1/chapters/project/{project_id}` | 项目章节列表 |
| `GET` | `/api/v1/chapters/volume/{volume_id}` | 卷内章节列表 |
| `POST` | `/api/v1/chapters/reorder` | 章节重排 |
| `GET` | `/api/v1/chapters/{chapter_id}` | 章节详情 |
| `PATCH` | `/api/v1/chapters/{chapter_id}` | 更新章节 |
| `DELETE` | `/api/v1/chapters/{chapter_id}` | 删除章节 |
| `POST` | `/api/v1/scenes` | 创建场景 |
| `GET` | `/api/v1/scenes/chapter/{chapter_id}` | 章节场景列表 |
| `POST` | `/api/v1/scenes/reorder` | 场景重排 |
| `GET` | `/api/v1/scenes/{scene_id}` | 场景详情 |
| `PATCH` | `/api/v1/scenes/{scene_id}` | 更新场景 |
| `DELETE` | `/api/v1/scenes/{scene_id}` | 删除场景 |

### Suggestions / Dependencies / Snapshots / Memories

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/suggestions` | Suggestion 列表 |
| `POST` | `/api/v1/suggestions` | 创建 Suggestion |
| `GET` | `/api/v1/suggestions/pending/count` | 待处理计数 |
| `GET` | `/api/v1/suggestions/target/{target_type}/{target_id}` | 目标对象 Suggestion |
| `GET` | `/api/v1/suggestions/{suggestion_id}` | Suggestion 详情 |
| `PATCH` | `/api/v1/suggestions/{suggestion_id}` | 更新 Suggestion |
| `DELETE` | `/api/v1/suggestions/{suggestion_id}` | 删除 Suggestion |
| `POST` | `/api/v1/suggestions/{suggestion_id}/action` | confirm / discard / commit |
| `GET` | `/api/v1/dependencies` | 依赖查询 |
| `POST` | `/api/v1/dependencies` | 创建依赖 |
| `POST` | `/api/v1/dependencies/analyze` | 影响分析 |
| `POST` | `/api/v1/dependencies/analyze/reverse/{target_type}/{target_id}` | 反向影响分析 |
| `GET` | `/api/v1/dependencies/source/{source_type}/{source_id}` | source 侧依赖 |
| `GET` | `/api/v1/dependencies/target/{target_type}/{target_id}` | target 侧依赖 |
| `GET` | `/api/v1/dependencies/{dependency_id}` | 依赖详情 |
| `PATCH` | `/api/v1/dependencies/{dependency_id}` | 更新依赖 |
| `DELETE` | `/api/v1/dependencies/{dependency_id}` | 删除依赖 |
| `GET` | `/api/v1/snapshots` | 快照列表 |
| `POST` | `/api/v1/snapshots` | 创建快照 |
| `GET` | `/api/v1/snapshots/count` | 快照计数 |
| `POST` | `/api/v1/snapshots/rollback` | 回滚到快照 |
| `GET` | `/api/v1/snapshots/target/{target_type}/{target_id}` | 目标对象快照列表 |
| `GET` | `/api/v1/snapshots/target/{target_type}/{target_id}/latest` | 目标对象最新快照 |
| `GET` | `/api/v1/snapshots/{snapshot_id}` | 快照详情 |
| `PATCH` | `/api/v1/snapshots/{snapshot_id}` | 更新快照 |
| `DELETE` | `/api/v1/snapshots/{snapshot_id}` | 删除快照 |
| `GET` | `/api/v1/snapshots/{snapshot_id}/data` | 快照数据 |
| `GET` | `/api/v1/memories` | 记忆列表 |
| `POST` | `/api/v1/memories` | 创建记忆 |
| `GET` | `/api/v1/memories/count` | 记忆计数 |
| `POST` | `/api/v1/memories/search` | 向量检索 |
| `GET` | `/api/v1/memories/type/{memory_type}` | 按类型列表 |
| `GET` | `/api/v1/memories/{memory_id}` | 记忆详情 |
| `PATCH` | `/api/v1/memories/{memory_id}` | 更新记忆 |
| `DELETE` | `/api/v1/memories/{memory_id}` | 删除记忆 |

### Agent

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/agent/profiles` | 项目可用 profile |
| `GET` | `/api/v1/agent/skills` | skill catalog |
| `GET` | `/api/v1/agent/risk-policies` | 风险策略 |
| `GET` | `/api/v1/agent/capabilities` | capability registry |
| `POST` | `/api/v1/agent/chat` | legacy chat |
| `POST` | `/api/v1/agent/chat/stream` | legacy chat stream |
| `POST` | `/api/v1/agent/continuity-check` | 连续性检查 |
| `POST` | `/api/v1/agent/auto-summarize` | 自动摘要 |
| `POST` | `/api/v1/agent/inline-edit` | 富文本内联改写 SSE |
| `POST` | `/api/v1/agent/threads` | 创建/获取默认线程 |
| `GET` | `/api/v1/agent/threads/{thread_id}` | 线程详情 |
| `POST` | `/api/v1/agent/threads/{thread_id}/messages` | 发送消息生成 run |
| `GET` | `/api/v1/agent/runs/{run_id}` | run 详情 |
| `POST` | `/api/v1/agent/runs/{run_id}/confirm` | 确认执行 |
| `POST` | `/api/v1/agent/runs/{run_id}/confirm-high-risk` | 二次确认 |
| `POST` | `/api/v1/agent/runs/{run_id}/cancel` | 取消 run |

## 3. 重点接口说明

### 3.1 项目导出

`GET /api/v1/projects/{project_id}/export?format=txt|markdown|docx`

- `txt`：纯文本导出
- `markdown`：Markdown 导出
- `docx`：Word 文档导出

### 3.2 时间线

`GET /api/v1/projects/{project_id}/timeline`

返回：

- `chapters[]`：按卷/章顺序的章节骨架
- `events[]`：挂接到章节/场景的 episode 记忆
- `unassigned_events[]`：无法归档到章节的事件记忆

### 3.3 章节 / 场景重排

- `POST /api/v1/chapters/reorder`
- `POST /api/v1/scenes/reorder`

服务端会使用临时偏移量重排，避免唯一约束冲突。

### 3.4 内联 AI 改写

`POST /api/v1/agent/inline-edit`

请求体：

```json
{
  "text": "原文片段",
  "operation": "rewrite",
  "context": {
    "project_id": "..."
  }
}
```

返回：SSE 流式文本片段。

## 4. 推荐调试方式

- 浏览器：`/docs`
- 原始 OpenAPI：`/openapi.json`
- 健康检查：`/api/v1/health`

本文件用于“分组理解接口面”；精确字段结构以运行中的 OpenAPI schema 为准。
