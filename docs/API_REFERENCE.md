# API Reference

最后更新：2026-03-16

本文档围绕当前代码生成的 OpenAPI 规格整理，并补充了双层规划体系的字段语义说明。

## 结构层级约定

- `Project.summary`：项目简介
- `Project.story_outline`：项目大纲
- `Volume.outline`：卷细纲总述
- `Chapter.outline`：章纲
- `Scene`：写作执行层

兼容规则：

- `POST /api/v1/chapters` 的 `volume_id` 仍为可选；省略时服务会自动挂到项目默认卷
- Suggestion 的 `target_type` 已支持 `project` 与 `volume`
- Agent 计划写入目标已支持项目大纲与卷细纲

## 基础信息

- Base URL: `http://localhost:8000/api/v1`
- 鉴权: 除 `GET /api/v1/health` 外，业务接口在配置 `ADMIN_API_KEY` 后需携带请求头。
- 默认鉴权头: `X-API-Key: <ADMIN_API_KEY>`（可由 `API_KEY_HEADER` 覆盖）
- JSON 请求默认头: `Content-Type: application/json`
- 文件上传请求头: `Content-Type: multipart/form-data`

## 统一响应与错误

- 成功响应: 2xx + 对应 schema（见每个接口的“成功响应”）
- 业务异常（400/404/409/503/500 等）默认结构：

```json
{
  "error": {
    "message": "错误描述",
    "details": {}
  }
}
```

- 参数校验异常（422）为 FastAPI 默认结构：

```json
{
  "detail": [
    {"loc": ["body", "field"], "msg": "...", "type": "..."}
  ]
}
```

## 接口清单

### 1. Root

- 接口名称: `Root`
- 标签: `untagged`
- 请求方法: `GET`
- URL 路径: `/`
- 请求头: 无鉴权要求
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: object
- 错误码: 无
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/'
```

### 2. Auto Summarize

- 接口名称: `Auto Summarize`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/auto-summarize`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `AutoSummarizeRequest`
- 成功响应: 200 -> application/json: AutoSummarizeResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/auto-summarize' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* AutoSummarizeRequest */ }'
```

### 3. Get Agent Capabilities

- 接口名称: `Get Agent Capabilities`
- 标签: `agent`
- 请求方法: `GET`
- URL 路径: `/api/v1/agent/capabilities`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: AgentCapabilityRegistryResponse
- 错误码: 无
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/agent/capabilities' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 4. Agent Chat

- 接口名称: `Agent Chat`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/chat`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `AgentChatRequest`
- 成功响应: 200 -> application/json: AgentChatResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/chat' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* AgentChatRequest */ }'
```

### 5. Agent Chat Stream

- 接口名称: `Agent Chat Stream`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/chat/stream`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `AgentChatRequest`
- 成功响应: 200 -> application/json: -
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/chat/stream' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* AgentChatRequest */ }'
```

### 6. Continuity Check

- 接口名称: `Continuity Check`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/continuity-check`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `ContinuityCheckRequest`
- 成功响应: 200 -> application/json: AgentChatResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/continuity-check' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* ContinuityCheckRequest */ }'
```

### 7. List Agent Profiles

- 接口名称: `List Agent Profiles`
- 标签: `agent`
- 请求方法: `GET`
- URL 路径: `/api/v1/agent/profiles`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<AgentProfileResponse>
- 错误码: 无
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/agent/profiles' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 8. Get Agent Risk Policies

- 接口名称: `Get Agent Risk Policies`
- 标签: `agent`
- 请求方法: `GET`
- URL 路径: `/api/v1/agent/risk-policies`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string | null, 可选)；`profile_id` (string | null, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: AgentRiskPolicyRegistryResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/agent/risk-policies' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 9. Get Run

- 接口名称: `Get Run`
- 标签: `agent`
- 请求方法: `GET`
- URL 路径: `/api/v1/agent/runs/{run_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `run_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: AgentRunResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/agent/runs/<run_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 10. Cancel Run

- 接口名称: `Cancel Run`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/runs/{run_id}/cancel`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `run_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: AgentRunActionResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/runs/<run_id>/cancel' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 11. Confirm Run

- 接口名称: `Confirm Run`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/runs/{run_id}/confirm`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `run_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: AgentRunActionResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/runs/<run_id>/confirm' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 12. Confirm High Risk Run

- 接口名称: `Confirm High Risk Run`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/runs/{run_id}/confirm-high-risk`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `run_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: AgentRunActionResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/runs/<run_id>/confirm-high-risk' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 13. Get Agent Skills

- 接口名称: `Get Agent Skills`
- 标签: `agent`
- 请求方法: `GET`
- URL 路径: `/api/v1/agent/skills`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string | null, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: AgentSkillCatalogResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/agent/skills' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 14. Create Or Get Thread

- 接口名称: `Create Or Get Thread`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/threads`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `AgentThreadCreateRequest`
- 成功响应: 200 -> application/json: AgentThreadResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/threads' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* AgentThreadCreateRequest */ }'
```

### 15. Get Thread

- 接口名称: `Get Thread`
- 标签: `agent`
- 请求方法: `GET`
- URL 路径: `/api/v1/agent/threads/{thread_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `thread_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: AgentThreadStateResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/agent/threads/<thread_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 16. Create Thread Message

- 接口名称: `Create Thread Message`
- 标签: `agent`
- 请求方法: `POST`
- URL 路径: `/api/v1/agent/threads/{thread_id}/messages`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `thread_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `AgentThreadMessageRequest`
- 成功响应: 200 -> application/json: AgentThreadMessageResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/agent/threads/<thread_id>/messages' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* AgentThreadMessageRequest */ }'
```

### 17. Create Chapter

- 接口名称: `Create Chapter`
- 标签: `chapters`
- 请求方法: `POST`
- URL 路径: `/api/v1/chapters`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `ChapterCreate`
- 成功响应: 201 -> application/json: ChapterResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/chapters' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* ChapterCreate */ }'
```

### 18. List Chapters By Project

- 接口名称: `List Chapters By Project`
- 标签: `chapters`
- 请求方法: `GET`
- URL 路径: `/api/v1/chapters/project/{project_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)
- 查询参数: `skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<ChapterResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/chapters/project/<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 19. List Chapters By Volume

- 接口名称: `List Chapters By Volume`
- 标签: `chapters`
- 请求方法: `GET`
- URL 路径: `/api/v1/chapters/volume/{volume_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `volume_id` (string, 必填)
- 查询参数: `skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<ChapterResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/chapters/volume/<volume_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 20. Get Chapter

- 接口名称: `Get Chapter`
- 标签: `chapters`
- 请求方法: `GET`
- URL 路径: `/api/v1/chapters/{chapter_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `chapter_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: ChapterResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/chapters/<chapter_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 21. Update Chapter

- 接口名称: `Update Chapter`
- 标签: `chapters`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/chapters/{chapter_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `chapter_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `ChapterUpdate`
- 成功响应: 200 -> application/json: ChapterResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/chapters/<chapter_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* ChapterUpdate */ }'
```

### 22. Delete Chapter

- 接口名称: `Delete Chapter`
- 标签: `chapters`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/chapters/{chapter_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `chapter_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: ChapterResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/chapters/<chapter_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 23. Create Character

- 接口名称: `Create Character`
- 标签: `characters`
- 请求方法: `POST`
- URL 路径: `/api/v1/characters`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `CharacterCreate`
- 成功响应: 201 -> application/json: CharacterResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/characters' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* CharacterCreate */ }'
```

### 24. List Characters By Project

- 接口名称: `List Characters By Project`
- 标签: `characters`
- 请求方法: `GET`
- URL 路径: `/api/v1/characters/project/{project_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)
- 查询参数: `skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<CharacterResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/characters/project/<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 25. Get Character

- 接口名称: `Get Character`
- 标签: `characters`
- 请求方法: `GET`
- URL 路径: `/api/v1/characters/{character_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `character_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: CharacterResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/characters/<character_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 26. Update Character

- 接口名称: `Update Character`
- 标签: `characters`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/characters/{character_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `character_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `CharacterUpdate`
- 成功响应: 200 -> application/json: CharacterResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/characters/<character_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* CharacterUpdate */ }'
```

### 27. Delete Character

- 接口名称: `Delete Character`
- 标签: `characters`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/characters/{character_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `character_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: CharacterResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/characters/<character_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 28. Query Dependencies

- 接口名称: `Query Dependencies`
- 标签: `dependencies`
- 请求方法: `GET`
- URL 路径: `/api/v1/dependencies`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)；`source_type` (string | null, 可选)；`source_id` (string | null, 可选)；`target_type` (string | null, 可选)；`target_id` (string | null, 可选)；`dependency_type` (string | null, 可选)；`skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<DependencyResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/dependencies?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 29. Create Dependency

- 接口名称: `Create Dependency`
- 标签: `dependencies`
- 请求方法: `POST`
- URL 路径: `/api/v1/dependencies`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `DependencyCreate`
- 成功响应: 201 -> application/json: DependencyResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/dependencies' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* DependencyCreate */ }'
```

### 30. Analyze Impact

- 接口名称: `Analyze Impact`
- 标签: `dependencies`
- 请求方法: `POST`
- URL 路径: `/api/v1/dependencies/analyze`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)
- 请求参数（Body）: `ImpactAnalysisRequest`
- 成功响应: 200 -> application/json: ImpactAnalysisResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/dependencies/analyze?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* ImpactAnalysisRequest */ }'
```

### 31. Analyze Reverse Impact

- 接口名称: `Analyze Reverse Impact`
- 标签: `dependencies`
- 请求方法: `POST`
- URL 路径: `/api/v1/dependencies/analyze/reverse/{target_type}/{target_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `target_type` (string, 必填)；`target_id` (string, 必填)
- 查询参数: `project_id` (string, 必填)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: ImpactAnalysisResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/dependencies/analyze/reverse/<target_type>/<target_id>?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 32. List Source Dependencies

- 接口名称: `List Source Dependencies`
- 标签: `dependencies`
- 请求方法: `GET`
- URL 路径: `/api/v1/dependencies/source/{source_type}/{source_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `source_type` (string, 必填)；`source_id` (string, 必填)
- 查询参数: `project_id` (string, 必填)；`skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<DependencyResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/dependencies/source/<source_type>/<source_id>?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 33. List Target Dependencies

- 接口名称: `List Target Dependencies`
- 标签: `dependencies`
- 请求方法: `GET`
- URL 路径: `/api/v1/dependencies/target/{target_type}/{target_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `target_type` (string, 必填)；`target_id` (string, 必填)
- 查询参数: `project_id` (string, 必填)；`skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<DependencyResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/dependencies/target/<target_type>/<target_id>?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 34. Get Dependency

- 接口名称: `Get Dependency`
- 标签: `dependencies`
- 请求方法: `GET`
- URL 路径: `/api/v1/dependencies/{dependency_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `dependency_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: DependencyResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/dependencies/<dependency_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 35. Update Dependency

- 接口名称: `Update Dependency`
- 标签: `dependencies`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/dependencies/{dependency_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `dependency_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `DependencyUpdate`
- 成功响应: 200 -> application/json: DependencyResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/dependencies/<dependency_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* DependencyUpdate */ }'
```

### 36. Delete Dependency

- 接口名称: `Delete Dependency`
- 标签: `dependencies`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/dependencies/{dependency_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `dependency_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: DependencyResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/dependencies/<dependency_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 37. Health Check

- 接口名称: `Health Check`
- 标签: `health`
- 请求方法: `GET`
- URL 路径: `/api/v1/health`
- 请求头: 无鉴权要求
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: HealthResponse
- 错误码: 无
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/health'
```

### 38. List Memories

- 接口名称: `List Memories`
- 标签: `memories`
- 请求方法: `GET`
- URL 路径: `/api/v1/memories`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)；`memory_type` (string | null, 可选)；`skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<MemoryResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/memories?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 39. Create Memory

- 接口名称: `Create Memory`
- 标签: `memories`
- 请求方法: `POST`
- URL 路径: `/api/v1/memories`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `MemoryCreate`
- 成功响应: 201 -> application/json: MemoryResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/memories' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* MemoryCreate */ }'
```

### 40. Count Memories

- 接口名称: `Count Memories`
- 标签: `memories`
- 请求方法: `GET`
- URL 路径: `/api/v1/memories/count`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)；`memory_type` (string | null, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: object
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/memories/count?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 41. Search Memories By Embedding

- 接口名称: `Search Memories By Embedding`
- 标签: `memories`
- 请求方法: `POST`
- URL 路径: `/api/v1/memories/search`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)
- 请求参数（Body）: `VectorSearchRequest`
- 成功响应: 200 -> application/json: VectorSearchResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/memories/search?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* VectorSearchRequest */ }'
```

### 42. List Memories By Type

- 接口名称: `List Memories By Type`
- 标签: `memories`
- 请求方法: `GET`
- URL 路径: `/api/v1/memories/type/{memory_type}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `memory_type` (string, 必填)
- 查询参数: `project_id` (string, 必填)；`skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<MemoryResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/memories/type/<memory_type>?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 43. Get Memory

- 接口名称: `Get Memory`
- 标签: `memories`
- 请求方法: `GET`
- URL 路径: `/api/v1/memories/{memory_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `memory_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: MemoryResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/memories/<memory_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 44. Update Memory

- 接口名称: `Update Memory`
- 标签: `memories`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/memories/{memory_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `memory_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `MemoryUpdate`
- 成功响应: 200 -> application/json: MemoryResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/memories/<memory_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* MemoryUpdate */ }'
```

### 45. Delete Memory

- 接口名称: `Delete Memory`
- 标签: `memories`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/memories/{memory_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `memory_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: MemoryResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/memories/<memory_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 46. List Projects

- 接口名称: `List Projects`
- 标签: `projects`
- 请求方法: `GET`
- URL 路径: `/api/v1/projects`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<ProjectResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/projects' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 47. Create Project

- 接口名称: `Create Project`
- 标签: `projects`
- 请求方法: `POST`
- URL 路径: `/api/v1/projects`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `ProjectCreate`
- 成功响应: 201 -> application/json: ProjectResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/projects' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* ProjectCreate */ }'
```

### 48. Import Project Package

- 接口名称: `Import Project Package`
- 标签: `project-package`
- 请求方法: `POST`
- URL 路径: `/api/v1/projects/import`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: multipart/form-data`
- 路径参数: 无
- 查询参数: `new_name` (string | null, 可选)
- 请求参数（Body）: `Body_import_project_package_api_v1_projects_import_post`
- 成功响应: 200 -> application/json: ProjectImportResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/projects/import' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@<path-to-file>'
```

### 49. Get Project

- 接口名称: `Get Project`
- 标签: `projects`
- 请求方法: `GET`
- URL 路径: `/api/v1/projects/{project_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: ProjectResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/projects/<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 50. Update Project

- 接口名称: `Update Project`
- 标签: `projects`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/projects/{project_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `project_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `ProjectUpdate`
- 成功响应: 200 -> application/json: ProjectResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/projects/<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* ProjectUpdate */ }'
```

### 51. Delete Project

- 接口名称: `Delete Project`
- 标签: `projects`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/projects/{project_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: ProjectResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/projects/<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 52. Export Project

- 接口名称: `Export Project`
- 标签: `export`
- 请求方法: `GET`
- URL 路径: `/api/v1/projects/{project_id}/export`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)
- 查询参数: `format` (string, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: -
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/projects/<project_id>/export' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 53. Export Project Package

- 接口名称: `Export Project Package`
- 标签: `project-package`
- 请求方法: `GET`
- URL 路径: `/api/v1/projects/{project_id}/package`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: -
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/projects/<project_id>/package' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 54. Create Scene

- 接口名称: `Create Scene`
- 标签: `scenes`
- 请求方法: `POST`
- URL 路径: `/api/v1/scenes`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `SceneCreate`
- 成功响应: 201 -> application/json: SceneResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/scenes' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* SceneCreate */ }'
```

### 55. List Scenes By Chapter

- 接口名称: `List Scenes By Chapter`
- 标签: `scenes`
- 请求方法: `GET`
- URL 路径: `/api/v1/scenes/chapter/{chapter_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `chapter_id` (string, 必填)
- 查询参数: `skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<SceneResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/scenes/chapter/<chapter_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 56. Get Scene

- 接口名称: `Get Scene`
- 标签: `scenes`
- 请求方法: `GET`
- URL 路径: `/api/v1/scenes/{scene_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `scene_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: SceneResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/scenes/<scene_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 57. Update Scene

- 接口名称: `Update Scene`
- 标签: `scenes`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/scenes/{scene_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `scene_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `SceneUpdate`
- 成功响应: 200 -> application/json: SceneResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/scenes/<scene_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* SceneUpdate */ }'
```

### 58. Delete Scene

- 接口名称: `Delete Scene`
- 标签: `scenes`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/scenes/{scene_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `scene_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: SceneResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/scenes/<scene_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 59. List Snapshots

- 接口名称: `List Snapshots`
- 标签: `snapshots`
- 请求方法: `GET`
- URL 路径: `/api/v1/snapshots`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)；`skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<SnapshotResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/snapshots?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 60. Create Snapshot

- 接口名称: `Create Snapshot`
- 标签: `snapshots`
- 请求方法: `POST`
- URL 路径: `/api/v1/snapshots`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `SnapshotCreate`
- 成功响应: 201 -> application/json: SnapshotResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/snapshots' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* SnapshotCreate */ }'
```

### 61. Count Snapshots

- 接口名称: `Count Snapshots`
- 标签: `snapshots`
- 请求方法: `GET`
- URL 路径: `/api/v1/snapshots/count`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)；`target_type` (string | null, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: object
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/snapshots/count?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 62. Rollback To Snapshot

- 接口名称: `Rollback To Snapshot`
- 标签: `snapshots`
- 请求方法: `POST`
- URL 路径: `/api/v1/snapshots/rollback`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)
- 请求参数（Body）: `RollbackRequest`
- 成功响应: 200 -> application/json: RollbackResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/snapshots/rollback?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* RollbackRequest */ }'
```

### 63. List Target Snapshots

- 接口名称: `List Target Snapshots`
- 标签: `snapshots`
- 请求方法: `GET`
- URL 路径: `/api/v1/snapshots/target/{target_type}/{target_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `target_type` (string, 必填)；`target_id` (string, 必填)
- 查询参数: `project_id` (string, 必填)；`skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<SnapshotResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/snapshots/target/<target_type>/<target_id>?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 64. Get Latest Snapshot

- 接口名称: `Get Latest Snapshot`
- 标签: `snapshots`
- 请求方法: `GET`
- URL 路径: `/api/v1/snapshots/target/{target_type}/{target_id}/latest`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `target_type` (string, 必填)；`target_id` (string, 必填)
- 查询参数: `project_id` (string, 必填)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: SnapshotResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/snapshots/target/<target_type>/<target_id>/latest?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 65. Get Snapshot

- 接口名称: `Get Snapshot`
- 标签: `snapshots`
- 请求方法: `GET`
- URL 路径: `/api/v1/snapshots/{snapshot_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `snapshot_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: SnapshotResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/snapshots/<snapshot_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 66. Update Snapshot

- 接口名称: `Update Snapshot`
- 标签: `snapshots`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/snapshots/{snapshot_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `snapshot_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `SnapshotUpdate`
- 成功响应: 200 -> application/json: SnapshotResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/snapshots/<snapshot_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* SnapshotUpdate */ }'
```

### 67. Delete Snapshot

- 接口名称: `Delete Snapshot`
- 标签: `snapshots`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/snapshots/{snapshot_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `snapshot_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: SnapshotResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/snapshots/<snapshot_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 68. Get Snapshot Data

- 接口名称: `Get Snapshot Data`
- 标签: `snapshots`
- 请求方法: `GET`
- URL 路径: `/api/v1/snapshots/{snapshot_id}/data`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `snapshot_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: object
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/snapshots/<snapshot_id>/data' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 69. List Suggestions

- 接口名称: `List Suggestions`
- 标签: `suggestions`
- 请求方法: `GET`
- URL 路径: `/api/v1/suggestions`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)；`skip` (integer, 可选)；`limit` (integer, 可选)；`status` (string | null, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<SuggestionResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/suggestions?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 70. Create Suggestion

- 接口名称: `Create Suggestion`
- 标签: `suggestions`
- 请求方法: `POST`
- URL 路径: `/api/v1/suggestions`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `SuggestionCreate`
- 成功响应: 201 -> application/json: SuggestionResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/suggestions' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* SuggestionCreate */ }'
```

### 71. Count Pending Suggestions

- 接口名称: `Count Pending Suggestions`
- 标签: `suggestions`
- 请求方法: `GET`
- URL 路径: `/api/v1/suggestions/pending/count`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: 无
- 查询参数: `project_id` (string, 必填)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: object
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/suggestions/pending/count?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 72. List Target Suggestions

- 接口名称: `List Target Suggestions`
- 标签: `suggestions`
- 请求方法: `GET`
- URL 路径: `/api/v1/suggestions/target/{target_type}/{target_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `target_type` (string, 必填)；`target_id` (string, 必填)
- 查询参数: `project_id` (string, 必填)；`skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<SuggestionResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/suggestions/target/<target_type>/<target_id>?project_id=<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 73. Get Suggestion

- 接口名称: `Get Suggestion`
- 标签: `suggestions`
- 请求方法: `GET`
- URL 路径: `/api/v1/suggestions/{suggestion_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `suggestion_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: SuggestionResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/suggestions/<suggestion_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 74. Update Suggestion

- 接口名称: `Update Suggestion`
- 标签: `suggestions`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/suggestions/{suggestion_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `suggestion_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `SuggestionUpdate`
- 成功响应: 200 -> application/json: SuggestionResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/suggestions/<suggestion_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* SuggestionUpdate */ }'
```

### 75. Delete Suggestion

- 接口名称: `Delete Suggestion`
- 标签: `suggestions`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/suggestions/{suggestion_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `suggestion_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: SuggestionResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/suggestions/<suggestion_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 76. Suggestion Action

- 接口名称: `Suggestion Action`
- 标签: `suggestions`
- 请求方法: `POST`
- URL 路径: `/api/v1/suggestions/{suggestion_id}/action`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `suggestion_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `SuggestionActionRequest`
- 成功响应: 200 -> application/json: SuggestionActionResult
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/suggestions/<suggestion_id>/action' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* SuggestionActionRequest */ }'
```

### 77. Create Volume

- 接口名称: `Create Volume`
- 标签: `volumes`
- 请求方法: `POST`
- URL 路径: `/api/v1/volumes`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `VolumeCreate`
- 成功响应: 201 -> application/json: VolumeResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/volumes' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* VolumeCreate */ }'
```

### 78. List Volumes By Project

- 接口名称: `List Volumes By Project`
- 标签: `volumes`
- 请求方法: `GET`
- URL 路径: `/api/v1/volumes/project/{project_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)
- 查询参数: `skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<VolumeResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/volumes/project/<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 79. Get Volume

- 接口名称: `Get Volume`
- 标签: `volumes`
- 请求方法: `GET`
- URL 路径: `/api/v1/volumes/{volume_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `volume_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: VolumeResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/volumes/<volume_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 80. Update Volume

- 接口名称: `Update Volume`
- 标签: `volumes`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/volumes/{volume_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `volume_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `VolumeUpdate`
- 成功响应: 200 -> application/json: VolumeResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/volumes/<volume_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* VolumeUpdate */ }'
```

### 81. Delete Volume

- 接口名称: `Delete Volume`
- 标签: `volumes`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/volumes/{volume_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `volume_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: VolumeResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/volumes/<volume_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 82. Create World Setting

- 接口名称: `Create World Setting`
- 标签: `world-settings`
- 请求方法: `POST`
- URL 路径: `/api/v1/world-settings`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: 无
- 查询参数: 无
- 请求参数（Body）: `WorldSettingCreate`
- 成功响应: 201 -> application/json: WorldSettingResponse
- 错误码: 422
- 请求示例:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/world-settings' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* WorldSettingCreate */ }'
```

### 83. List World Settings By Project

- 接口名称: `List World Settings By Project`
- 标签: `world-settings`
- 请求方法: `GET`
- URL 路径: `/api/v1/world-settings/project/{project_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)
- 查询参数: `skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<WorldSettingResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/world-settings/project/<project_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 84. List World Settings By Category

- 接口名称: `List World Settings By Category`
- 标签: `world-settings`
- 请求方法: `GET`
- URL 路径: `/api/v1/world-settings/project/{project_id}/category/{category}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `project_id` (string, 必填)；`category` (string, 必填)
- 查询参数: `skip` (integer, 可选)；`limit` (integer, 可选)
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: array<WorldSettingResponse>
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/world-settings/project/<project_id>/category/<category>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 85. Get World Setting

- 接口名称: `Get World Setting`
- 标签: `world-settings`
- 请求方法: `GET`
- URL 路径: `/api/v1/world-settings/{setting_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `setting_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: WorldSettingResponse
- 错误码: 422
- 请求示例:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/world-settings/<setting_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 86. Update World Setting

- 接口名称: `Update World Setting`
- 标签: `world-settings`
- 请求方法: `PATCH`
- URL 路径: `/api/v1/world-settings/{setting_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
  - `Content-Type: application/json`
- 路径参数: `setting_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `WorldSettingUpdate`
- 成功响应: 200 -> application/json: WorldSettingResponse
- 错误码: 422
- 请求示例:

```bash
curl -X PATCH \
  'http://localhost:8000/api/v1/world-settings/<setting_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{ /* WorldSettingUpdate */ }'
```

### 87. Delete World Setting

- 接口名称: `Delete World Setting`
- 标签: `world-settings`
- 请求方法: `DELETE`
- URL 路径: `/api/v1/world-settings/{setting_id}`
- 请求头:
  - `X-API-Key: <ADMIN_API_KEY>`
- 路径参数: `setting_id` (string, 必填)
- 查询参数: 无
- 请求参数（Body）: `-`
- 成功响应: 200 -> application/json: WorldSettingResponse
- 错误码: 422
- 请求示例:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/world-settings/<setting_id>' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

## 常见错误码说明

| 错误码 | 含义 | 常见触发场景 |
|---|---|---|
| 400 | 业务参数不合法 | 业务校验失败、fixture 缺失、策略冲突 |
| 401 | 未认证 | 缺少 `X-API-Key` |
| 403 | 禁止访问 | `X-API-Key` 错误 |
| 404 | 资源不存在 | 项目/章节/快照等 ID 不存在 |
| 409 | 冲突 | 唯一约束冲突 |
| 422 | 协议校验失败 | 请求体或参数类型不匹配 |
| 500 | 服务器错误 | 未捕获异常 |
| 503 | 外部服务不可用 | LLM/Embedding 服务不可达 |

## 关键业务示例

### 示例 1：创建项目
```bash
curl -X POST 'http://localhost:8000/api/v1/projects' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "长篇测试项目",
    "genre": "xianxia",
    "target_audience": "adult",
    "agent_profile_id": "default"
  }'
```

### 示例 2：生成并确认 Agent 计划
```bash
curl -X POST 'http://localhost:8000/api/v1/agent/threads' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"project_id": "<project_id>"}'

curl -X POST 'http://localhost:8000/api/v1/agent/threads/<thread_id>/messages' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"content": "创建一个测试人物", "context": {}, "stream": false}'

curl -X POST 'http://localhost:8000/api/v1/agent/runs/<run_id>/confirm' \
  -H 'X-API-Key: <ADMIN_API_KEY>'
```

### 示例 3：导出并导入项目包
```bash
curl -X GET 'http://localhost:8000/api/v1/projects/<project_id>/package' \
  -H 'X-API-Key: <ADMIN_API_KEY>' -o project_package.zip

curl -X POST 'http://localhost:8000/api/v1/projects/import?new_name=导入副本' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -F 'file=@./project_package.zip'
```

## Schema 字段索引

以下字段定义用于补充“请求参数/响应格式”的结构化说明。

### AgentActiveBundleCollectionsResponse

- 类型: `object`
- 描述: Collection limits and realized counts included in the planner bundle.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `characters_count` | `integer` | 否 |  |
| `characters_limit` | `integer` | 否 |  |
| `world_settings_count` | `integer` | 否 |  |
| `world_settings_limit` | `integer` | 否 |  |
| `chapters_count` | `integer` | 否 |  |
| `chapters_limit` | `integer` | 否 |  |
| `current_scenes_count` | `integer` | 否 |  |
| `current_scenes_limit` | `integer` | 否 |  |
| `recent_run_digest_count` | `integer` | 否 |  |
| `recent_run_digest_limit` | `integer` | 否 |  |

### AgentActiveBundleContractResponse

- 类型: `object`
- 描述: Stable description of which context sections were assembled for planning.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `contract_version` | `string` | 是 |  |
| `source` | `string(live_context, checkpoint_plus_live_context, checkpoint_snapshot)` | 是 |  |
| `included_sections` | `array<string>` | 否 |  |
| `focused_object_types` | `array<string>` | 否 |  |
| `checkpoint_id` | `string \| null` | 否 |  |
| `includes_thread_summary` | `boolean` | 否 |  |
| `includes_recent_run_digest` | `boolean` | 否 |  |
| `collections` | `AgentActiveBundleCollectionsResponse` | 是 |  |

### AgentAppliedRiskPolicyResponse

- 类型: `object`
- 描述: One policy application recorded on a concrete run.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `policy_id` | `string(create_only, standard_updates, content_append, content_rewrite, long_form_overwrite, multi_object_write)` | 是 |  |
| `name` | `string` | 是 |  |
| `scope` | `string(operation, run)` | 是 |  |
| `description` | `string` | 是 |  |
| `risk_level` | `string(low, medium, high)` | 是 |  |
| `confirmation_gate` | `string(none, single, double)` | 是 |  |
| `requires_secondary_confirmation` | `boolean` | 否 |  |
| `matched_operation_positions` | `array<integer>` | 否 |  |

### AgentCapabilityExecutionRecordResponse

- 类型: `object`
- 描述: Execution record for one internal capability.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `record_id` | `string` | 是 |  |
| `source_role` | `string(planner, researcher, writer, editor, continuity, executor)` | 是 |  |
| `status` | `string(planned, completed, failed, skipped)` | 是 |  |
| `tool_scope` | `array<string>` | 否 |  |
| `input_summary` | `string \| null` | 否 |  |
| `output_summary` | `string \| null` | 否 |  |
| `attempt_count` | `integer` | 否 |  |

### AgentCapabilityPolicyResponse

- 类型: `object`
- 描述: Stable policy contract for one internal capability.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `execution_phase` | `string(plan, build)` | 是 |  |
| `source_role` | `string(planner, researcher, writer, editor, continuity, executor)` | 是 |  |
| `confirmation_gate` | `string(none, single, double)` | 是 |  |
| `internal_only` | `boolean` | 否 |  |
| `requires_confirmation` | `boolean` | 否 |  |

### AgentCapabilityRegistryResponse

- 类型: `object`
- 描述: Stable registry of capability contracts available to the workflow.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `registry_version` | `string` | 是 |  |
| `capabilities` | `array<AgentCapabilityResponse>` | 否 |  |

### AgentCapabilityResponse

- 类型: `object`
- 描述: One stable internal capability exposed with the run contract.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `capability_id` | `string` | 是 |  |
| `name` | `string` | 是 |  |
| `kind` | `string(read_search, planning, writing, editing, verification)` | 是 |  |
| `description` | `string` | 是 |  |
| `tool_scope` | `array<string>` | 否 |  |
| `policy` | `AgentCapabilityPolicyResponse` | 是 |  |
| `execution_record` | `AgentCapabilityExecutionRecordResponse \| null` | 否 |  |

### AgentChatRequest

- 类型: `object`
- 描述: Legacy request schema for the previous chat endpoint.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_id` | `string` | 是 | Project UUID |
| `message` | `string` | 是 | User message |
| `history` | `array<object>` | 否 | Chat history |
| `context` | `object` | 否 | Extra context data |

### AgentChatResponse

- 类型: `object`
- 描述: Legacy response schema for the previous chat endpoint.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `message` | `string` | 是 | Agent response message |
| `suggestions` | `array<object>` | 否 | Generated suggestions |
| `metadata` | `object` | 否 | Agent metadata |

### AgentCompactPolicyResponse

- 类型: `object`
- 描述: Stable compact policy applied by the thread planner.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `policy_version` | `string` | 是 |  |
| `message_threshold` | `integer` | 是 |  |
| `run_threshold` | `integer` | 是 |  |
| `char_threshold` | `integer` | 是 |  |
| `recent_window_limit` | `integer` | 是 |  |
| `checkpoint_delta_limit` | `integer` | 是 |  |

### AgentCompactionBoundaryResponse

- 类型: `object`
- 描述: Boundary metadata captured when a checkpoint was created.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `history_mode` | `string(recent_window, checkpoint_delta)` | 是 |  |
| `source_message_count` | `integer` | 是 |  |
| `source_run_count` | `integer` | 是 |  |

### AgentExecutionChildUnitResponse

- 类型: `object`
- 描述: Stable contract for one internal child unit inside a workflow phase.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `unit_id` | `string` | 是 |  |
| `role` | `string(planner, researcher, writer, editor, continuity, executor)` | 是 |  |
| `phase` | `string(plan, build)` | 是 |  |
| `stage` | `string(preview, pre_execution, execution)` | 是 |  |
| `mode` | `string(restricted, gated)` | 是 |  |
| `title` | `string` | 是 |  |
| `description` | `string` | 是 |  |
| `tool_scope` | `array<string>` | 否 |  |
| `capability_ids` | `array<string>` | 否 |  |
| `depends_on` | `array<string>` | 否 |  |
| `operation_positions` | `array<integer>` | 否 |  |
| `confirmation_gate` | `string(none, single, double)` | 是 |  |
| `requires_confirmation` | `boolean` | 否 |  |
| `internal_only` | `boolean` | 否 |  |

### AgentExecutionContractResponse

- 类型: `object`
- 描述: Stable child unit contract surfaced with each run.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `registry_version` | `string` | 是 |  |
| `phases` | `array<AgentExecutionPhaseResponse>` | 否 |  |

### AgentExecutionPhaseResponse

- 类型: `object`
- 描述: Stable run-level contract for one workflow phase.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `phase` | `string(plan, build)` | 是 |  |
| `mode` | `string(restricted, gated)` | 是 |  |
| `allowed_permission_levels` | `array<string(read_search, standard_write, high_risk_write)>` | 否 |  |
| `tool_scope` | `array<string>` | 否 |  |
| `role_scope` | `array<string(planner, researcher, writer, editor, continuity)>` | 否 |  |
| `confirmation_gate` | `string(none, single, double)` | 是 |  |
| `requires_confirmation` | `boolean` | 否 |  |
| `requires_secondary_confirmation` | `boolean` | 否 |  |
| `operation_count` | `integer` | 否 |  |
| `child_units` | `array<AgentExecutionChildUnitResponse>` | 否 |  |
| `capabilities` | `array<AgentCapabilityResponse>` | 否 |  |

### AgentMessageResponse

- 类型: `object`
- 描述: Message persisted in an agent thread.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | 是 |  |
| `thread_id` | `string` | 是 |  |
| `role` | `string(user, assistant, system)` | 是 |  |
| `content` | `string` | 是 |  |
| `meta` | `object` | 否 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### AgentOperationResponse

- 类型: `object`
- 描述: A single planned or executed operation.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | 是 |  |
| `run_id` | `string` | 是 |  |
| `position` | `integer` | 是 |  |
| `tool_name` | `string` | 是 |  |
| `target_type` | `string \| null` | 否 |  |
| `target_id` | `string \| null` | 否 |  |
| `target_display` | `string \| null` | 否 |  |
| `description` | `string` | 是 |  |
| `reason` | `string \| null` | 否 |  |
| `payload` | `object` | 是 |  |
| `preview` | `OperationPreview` | 是 |  |
| `permission_level` | `string(read_search, standard_write, high_risk_write)` | 是 |  |
| `risk_level` | `string(low, medium, high)` | 是 |  |
| `requires_secondary_confirmation` | `boolean` | 是 |  |
| `status` | `string(planned, executed, failed, cancelled)` | 是 |  |
| `verification_status` | `string(pending, passed, failed, skipped)` | 是 |  |
| `verification_summary` | `string \| null` | 否 |  |
| `execution_result` | `object \| null` | 否 |  |
| `error_message` | `string \| null` | 否 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### AgentPlannerWindowResponse

- 类型: `object`
- 描述: Resolved planner input window for one run.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `history_mode` | `string(recent_window, checkpoint_delta)` | 是 |  |
| `history_message_count` | `integer` | 是 |  |
| `retained_message_limit` | `integer` | 是 |  |
| `checkpoint_id` | `string \| null` | 否 |  |
| `checkpoint_available` | `boolean` | 否 |  |
| `compact_policy_version` | `string \| null` | 否 |  |

### AgentProfileResponse

- 类型: `object`
- 描述: Available project-level agent profile.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | 是 |  |
| `name` | `string` | 是 |  |
| `description` | `string` | 是 |  |
| `builtin` | `boolean` | 是 |  |
| `root` | `string` | 是 |  |

### AgentRetainedWindowResponse

- 类型: `object`
- 描述: Concrete history slice retained for one planner invocation.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `history_mode` | `string(recent_window, checkpoint_delta)` | 是 |  |
| `message_count` | `integer` | 是 |  |
| `character_count` | `integer` | 是 |  |
| `retained_message_limit` | `integer` | 是 |  |
| `oldest_message_id` | `string \| null` | 否 |  |
| `newest_message_id` | `string \| null` | 否 |  |
| `checkpoint_id` | `string \| null` | 否 |  |
| `compact_policy_version` | `string \| null` | 否 |  |
| `roles` | `array<string>` | 否 |  |

### AgentRiskPolicyRegistryResponse

- 类型: `object`
- 描述: Stable registry of risk policies used by the run classifier.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `policy_version` | `string` | 是 |  |
| `policies` | `array<AgentRiskPolicyResponse>` | 否 |  |

### AgentRiskPolicyResponse

- 类型: `object`
- 描述: Stable risk classification policy exposed independently from one run.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `policy_id` | `string(create_only, standard_updates, content_append, content_rewrite, long_form_overwrite, multi_object_write)` | 是 |  |
| `name` | `string` | 是 |  |
| `scope` | `string(operation, run)` | 是 |  |
| `description` | `string` | 是 |  |
| `risk_level` | `string(low, medium, high)` | 是 |  |
| `confirmation_gate` | `string(none, single, double)` | 是 |  |
| `requires_secondary_confirmation` | `boolean` | 否 |  |
| `tool_scope` | `array<string>` | 否 |  |

### AgentRunActionResponse

- 类型: `object`
- 描述: Response for confirm/cancel actions.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run` | `AgentRunResponse` | 是 |  |

### AgentRunResponse

- 类型: `object`
- 描述: An executable plan generated from one user request.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | 是 |  |
| `thread_id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `user_message_id` | `string \| null` | 否 |  |
| `assistant_message_id` | `string \| null` | 否 |  |
| `revision_of_run_id` | `string \| null` | 否 |  |
| `status` | `string(draft, awaiting_confirmation, awaiting_high_risk_confirmation, executing, completed, failed, cancelled, superseded)` | 是 |  |
| `summary` | `string \| null` | 否 |  |
| `error_message` | `string \| null` | 否 |  |
| `warning_message` | `string \| null` | 否 |  |
| `verification_status` | `string(pending, passed, failed, skipped)` | 是 |  |
| `verification_summary` | `string \| null` | 否 |  |
| `execution_contract` | `AgentExecutionContractResponse \| null` | 否 |  |
| `risk_summary` | `AgentRunRiskSummaryResponse \| null` | 否 |  |
| `compact_policy` | `AgentCompactPolicyResponse \| null` | 否 |  |
| `planner_window` | `AgentPlannerWindowResponse \| null` | 否 |  |
| `retained_window` | `AgentRetainedWindowResponse \| null` | 否 |  |
| `active_bundle_contract` | `AgentActiveBundleContractResponse \| null` | 否 |  |
| `meta` | `object` | 否 |  |
| `confirmed_at` | `string \| null` | 否 |  |
| `secondary_confirmed_at` | `string \| null` | 否 |  |
| `started_at` | `string \| null` | 否 |  |
| `completed_at` | `string \| null` | 否 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |
| `operations` | `array<AgentOperationResponse>` | 否 |  |
| `subtasks` | `array<AgentSubtaskResponse>` | 否 |  |

### AgentRunRiskSummaryResponse

- 类型: `object`
- 描述: Stable run-level aggregation of write risk and confirmation gates.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `policy_version` | `string` | 是 |  |
| `overall_risk_level` | `string(low, medium, high)` | 是 |  |
| `confirmation_gate` | `string(none, single, double)` | 是 |  |
| `requires_confirmation` | `boolean` | 是 |  |
| `requires_secondary_confirmation` | `boolean` | 是 |  |
| `total_operations` | `integer` | 否 |  |
| `low_risk_operation_count` | `integer` | 否 |  |
| `medium_risk_operation_count` | `integer` | 否 |  |
| `high_risk_operation_count` | `integer` | 否 |  |
| `high_risk_operation_positions` | `array<integer>` | 否 |  |
| `secondary_confirmation_operation_positions` | `array<integer>` | 否 |  |
| `applied_policies` | `array<AgentAppliedRiskPolicyResponse>` | 否 |  |
| `summary` | `string` | 是 |  |

### AgentSkillCatalogResponse

- 类型: `object`
- 描述: Active planner and operation skill catalog.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `profile_id` | `string` | 是 |  |
| `profile_name` | `string` | 是 |  |
| `builtin` | `boolean` | 是 |  |
| `source_roots` | `array<string>` | 否 |  |
| `planner` | `AgentSkillSummaryResponse` | 是 |  |
| `operations` | `array<AgentSkillSummaryResponse>` | 否 |  |

### AgentSkillSummaryResponse

- 类型: `object`
- 描述: Serializable metadata for one loaded planner or operation skill.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | `string` | 是 |  |
| `description` | `string` | 是 |  |
| `kind` | `string` | 是 |  |
| `tool_name` | `string \| null` | 否 |  |
| `source` | `string` | 是 |  |
| `payload_contract` | `string \| null` | 否 |  |
| `references` | `array<string>` | 否 |  |

### AgentSubtaskAttemptResponse

- 类型: `object`
- 描述: One attempt within a child execution unit.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `attempt_number` | `integer` | 是 |  |
| `source` | `string` | 是 |  |
| `accepted` | `boolean` | 是 |  |
| `validation_status` | `string(passed, recovered, failed)` | 是 |  |
| `summary` | `string` | 是 |  |

### AgentSubtaskResponse

- 类型: `object`
- 描述: Internal subtask summary exposed with a run.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | 是 |  |
| `run_id` | `string` | 是 |  |
| `position` | `integer` | 是 |  |
| `role` | `string(planner, researcher, writer, editor, continuity)` | 是 |  |
| `title` | `string` | 是 |  |
| `status` | `string(planned, completed, failed, skipped)` | 是 |  |
| `summary` | `string \| null` | 否 |  |
| `error_message` | `string \| null` | 否 |  |
| `child_trace` | `AgentSubtaskTraceResponse \| null` | 否 |  |
| `meta` | `object` | 否 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### AgentSubtaskTraceResponse

- 类型: `object`
- 描述: Stable child execution trace for one internal subtask.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `unit_id` | `string` | 是 |  |
| `role` | `string(planner, researcher, writer, editor, continuity)` | 是 |  |
| `execution_phase` | `string(plan, build_validation)` | 是 |  |
| `retry_strategy` | `string(service_only, planner_then_service_fallback)` | 是 |  |
| `depends_on` | `array<string>` | 否 |  |
| `operation_positions` | `array<integer>` | 否 |  |
| `tool_scope` | `array<string>` | 否 |  |
| `input_summary` | `string \| null` | 否 |  |
| `output_summary` | `string \| null` | 否 |  |
| `attempts` | `array<AgentSubtaskAttemptResponse>` | 否 |  |

### AgentThreadCheckpointResponse

- 类型: `object`
- 描述: Compressed thread state snapshot exposed to the workspace.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | 是 |  |
| `thread_id` | `string` | 是 |  |
| `profile_id` | `string` | 是 |  |
| `thread_summary` | `string` | 是 |  |
| `active_object_bundle` | `object` | 否 |  |
| `recent_run_digest` | `object` | 否 |  |
| `source_message_count` | `integer` | 是 |  |
| `source_run_count` | `integer` | 是 |  |
| `total_context_characters` | `integer` | 是 |  |
| `compact_policy` | `AgentCompactPolicyResponse \| null` | 否 |  |
| `compaction_boundary` | `AgentCompactionBoundaryResponse \| null` | 否 |  |
| `active_bundle_contract` | `AgentActiveBundleContractResponse \| null` | 否 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### AgentThreadCreateRequest

- 类型: `object`
- 描述: Create or fetch the default thread for a project.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_id` | `string` | 是 |  |

### AgentThreadMessageRequest

- 类型: `object`
- 描述: User message sent into a thread.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `content` | `string` | 是 |  |
| `context` | `object` | 否 |  |
| `stream` | `boolean` | 否 |  |

### AgentThreadMessageResponse

- 类型: `object`
- 描述: Planner response for a new thread message.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `thread` | `AgentThreadResponse` | 是 |  |
| `user_message` | `AgentMessageResponse` | 是 |  |
| `assistant_message` | `AgentMessageResponse` | 是 |  |
| `run` | `AgentRunResponse \| null` | 否 |  |

### AgentThreadResponse

- 类型: `object`
- 描述: Thread metadata.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `title` | `string` | 是 |  |
| `is_default` | `boolean` | 是 |  |
| `meta` | `object` | 否 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### AgentThreadStateResponse

- 类型: `object`
- 描述: Thread view used by the Agent Workspace.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `thread` | `AgentThreadResponse` | 是 |  |
| `messages` | `array<AgentMessageResponse>` | 否 |  |
| `recent_runs` | `array<AgentRunResponse>` | 否 |  |
| `current_run` | `AgentRunResponse \| null` | 否 |  |
| `latest_checkpoint` | `AgentThreadCheckpointResponse \| null` | 否 |  |

### AutoSummarizeRequest

- 类型: `object`
- 描述: Request schema for legacy auto-summarize.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_id` | `string` | 是 |  |
| `chapter_id` | `string` | 是 |  |
| `content` | `string` | 是 |  |

### AutoSummarizeResponse

- 类型: `object`
- 描述: Response schema for legacy auto-summarize.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `memories` | `array<object>` | 是 |  |
| `count` | `integer` | 是 |  |

### Body_import_project_package_api_v1_projects_import_post

- 类型: `object`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | `string` | 是 |  |

### ChapterCreate

- 类型: `object`
- 描述: Schema for creating a chapter.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `chapter_number` | `integer` | 是 |  |
| `title` | `string \| null` | 否 |  |
| `outline` | `string \| null` | 否 | 章纲内容 |
| `content` | `string \| null` | 否 |  |
| `status` | `string(draft, writing, completed)` | 否 |  |
| `notes` | `string \| null` | 否 |  |
| `project_id` | `string` | 是 |  |
| `volume_id` | `string \| null` | 否 | 所属卷；省略时自动挂到默认卷 |

### ChapterResponse

- 类型: `object`
- 描述: Schema for chapter response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `chapter_number` | `integer` | 是 |  |
| `title` | `string \| null` | 否 |  |
| `outline` | `string \| null` | 否 | 章纲内容 |
| `content` | `string \| null` | 否 |  |
| `status` | `string(draft, writing, completed)` | 否 |  |
| `notes` | `string \| null` | 否 |  |
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `volume_id` | `string \| null` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### ChapterUpdate

- 类型: `object`
- 描述: Schema for updating a chapter.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `chapter_number` | `integer \| null` | 否 |  |
| `title` | `string \| null` | 否 |  |
| `outline` | `string \| null` | 否 | 章纲内容 |
| `content` | `string \| null` | 否 |  |
| `status` | `string(draft, writing, completed) \| null` | 否 |  |
| `notes` | `string \| null` | 否 |  |
| `volume_id` | `string \| null` | 否 |  |

### CharacterCreate

- 类型: `object`
- 描述: Schema for creating a character.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | `string` | 是 |  |
| `role` | `string \| null` | 否 |  |
| `profile` | `object` | 否 |  |
| `relationships` | `object` | 否 |  |
| `arc_state` | `object` | 否 |  |
| `notes` | `string \| null` | 否 |  |
| `project_id` | `string` | 是 |  |

### CharacterResponse

- 类型: `object`
- 描述: Schema for character response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | `string` | 是 |  |
| `role` | `string \| null` | 否 |  |
| `profile` | `object` | 否 |  |
| `relationships` | `object` | 否 |  |
| `arc_state` | `object` | 否 |  |
| `notes` | `string \| null` | 否 |  |
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### CharacterUpdate

- 类型: `object`
- 描述: Schema for updating a character.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | `string \| null` | 否 |  |
| `role` | `string \| null` | 否 |  |
| `profile` | `object \| null` | 否 |  |
| `relationships` | `object \| null` | 否 |  |
| `arc_state` | `object \| null` | 否 |  |
| `notes` | `string \| null` | 否 |  |

### ContinuityCheckRequest

- 类型: `object`
- 描述: Request schema for legacy continuity check.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_id` | `string` | 是 |  |
| `content` | `string` | 是 |  |

### DependencyCreate

- 类型: `object`
- 描述: Schema for creating a dependency.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 | Type of the source object |
| `source_id` | `string` | 是 | ID of the source object |
| `target_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 | Type of the target object |
| `target_id` | `string` | 是 | ID of the target object |
| `dependency_type` | `string(references, influences, contains, precedes) \| null` | 否 | Type of dependency relationship |
| `project_id` | `string` | 是 |  |

### DependencyResponse

- 类型: `object`
- 描述: Schema for dependency response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 | Type of the source object |
| `source_id` | `string` | 是 | ID of the source object |
| `target_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 | Type of the target object |
| `target_id` | `string` | 是 | ID of the target object |
| `dependency_type` | `string(references, influences, contains, precedes) \| null` | 否 | Type of dependency relationship |
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### DependencyUpdate

- 类型: `object`
- 描述: Schema for updating a dependency.<br><br>Note: Only dependency_type can be updated via PATCH.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `dependency_type` | `string(references, influences, contains, precedes) \| null` | 否 |  |

### HTTPValidationError

- 类型: `object`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `detail` | `array<ValidationError>` | 否 |  |

### HealthResponse

- 类型: `object`
- 描述: Health check response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `status` | `string` | 是 |  |
| `version` | `string` | 是 |  |
| `mode` | `string` | 是 |  |
| `auth_required` | `boolean` | 是 |  |
| `api_key_header` | `string \| null` | 否 |  |
| `database` | `string \| null` | 否 |  |
| `redis` | `string \| null` | 否 |  |

### ImpactAnalysisRequest

- 类型: `object`
- 描述: Schema for impact analysis request.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 | Type of the source object being modified |
| `source_id` | `string` | 是 | ID of the source object being modified |

### ImpactAnalysisResponse

- 类型: `object`
- 描述: Schema for impact analysis response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 |  |
| `source_id` | `string` | 是 |  |
| `impacted_objects` | `array<ImpactDetail>` | 是 |  |
| `total_count` | `integer` | 是 |  |
| `analysis_summary` | `string \| null` | 否 |  |

### ImpactDetail

- 类型: `object`
- 描述: Detail of a single impact.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 |  |
| `target_id` | `string` | 是 |  |
| `dependency_type` | `string(references, influences, contains, precedes) \| null` | 是 |  |
| `description` | `string \| null` | 否 |  |

### MemoryCreate

- 类型: `object`
- 描述: Schema for creating a memory.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `memory_type` | `string` | 是 | Type of memory (episode, semantic, fact) |
| `content` | `string` | 是 | Memory content text |
| `meta` | `object` | 否 | Additional metadata |
| `project_id` | `string` | 是 | Project ID this memory belongs to |
| `embedding` | `array<number> \| null` | 否 | Vector embedding (4096 dimensions) |
| `auto_embed` | `boolean` | 否 | Automatically generate embedding from content |

### MemoryMatch

- 类型: `object`
- 描述: A single memory match from vector search.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `string` | 是 |  |
| `memory_type` | `string` | 是 |  |
| `content` | `string` | 是 |  |
| `meta` | `object` | 是 |  |
| `similarity` | `number` | 是 | Cosine similarity score (0-1) |

### MemoryResponse

- 类型: `object`
- 描述: Schema for memory response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `memory_type` | `string` | 是 | Type of memory (episode, semantic, fact) |
| `content` | `string` | 是 | Memory content text |
| `meta` | `object` | 否 | Additional metadata |
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `embedding` | `array<number> \| null` | 否 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### MemoryUpdate

- 类型: `object`
- 描述: Schema for updating a memory.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `content` | `string \| null` | 否 |  |
| `memory_type` | `string \| null` | 否 |  |
| `meta` | `object \| null` | 否 |  |
| `embedding` | `array<number> \| null` | 否 |  |
| `auto_embed` | `boolean \| null` | 否 | Automatically regenerate embedding from content if content changes |

### OperationPreview

- 类型: `object`
- 描述: Preview payload shown before execution.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `changed_fields` | `array<string>` | 否 |  |
| `before_summary` | `string \| null` | 否 |  |
| `after_summary` | `string \| null` | 否 |  |
| `diff` | `string \| null` | 否 |  |
| `reason` | `string \| null` | 否 |  |

### ProjectCreate

- 类型: `object`
- 描述: Schema for creating a project.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | `string` | 是 |  |
| `genre` | `string \| null` | 否 |  |
| `target_audience` | `string \| null` | 否 |  |
| `target_word_count` | `integer \| null` | 否 |  |
| `summary` | `string \| null` | 否 |  |
| `story_outline` | `string \| null` | 否 | 项目级总纲，区别于简介 |
| `notes` | `string \| null` | 否 |  |
| `agent_profile_id` | `string` | 否 |  |
| `meta` | `object` | 否 |  |
| `status` | `string(drafting, writing, revising, completed)` | 否 |  |

### ProjectImportResponse

- 类型: `object`
- 描述: Response for project import operation.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_id` | `string` | 是 | New project ID |
| `project_name` | `string` | 是 | New project name |
| `imported_counts` | `object` | 是 | Counts of imported objects by type |
| `warnings` | `array<ProjectImportWarning>` | 否 | Warnings generated during import |

### ProjectImportWarning

- 类型: `object`
- 描述: A warning generated during project import.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `code` | `string` | 是 | Warning code |
| `message` | `string` | 是 | Human-readable warning message |
| `details` | `object \| null` | 否 | Additional details |

### ProjectResponse

- 类型: `object`
- 描述: Schema for project response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | `string` | 是 |  |
| `genre` | `string \| null` | 否 |  |
| `target_audience` | `string \| null` | 否 |  |
| `target_word_count` | `integer \| null` | 否 |  |
| `summary` | `string \| null` | 否 |  |
| `story_outline` | `string \| null` | 否 | 项目级总纲，区别于简介 |
| `notes` | `string \| null` | 否 |  |
| `agent_profile_id` | `string` | 否 |  |
| `meta` | `object` | 否 |  |
| `id` | `string` | 是 |  |
| `status` | `string(drafting, writing, revising, completed)` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### ProjectUpdate

- 类型: `object`
- 描述: Schema for updating a project.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | `string \| null` | 否 |  |
| `genre` | `string \| null` | 否 |  |
| `target_audience` | `string \| null` | 否 |  |
| `target_word_count` | `integer \| null` | 否 |  |
| `status` | `string(drafting, writing, revising, completed) \| null` | 否 |  |
| `summary` | `string \| null` | 否 |  |
| `story_outline` | `string \| null` | 否 | 项目级总纲，区别于简介 |
| `notes` | `string \| null` | 否 |  |
| `agent_profile_id` | `string \| null` | 否 |  |
| `meta` | `object \| null` | 否 |  |

### RollbackRequest

- 类型: `object`
- 描述: Schema for rolling back to a snapshot.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `snapshot_id` | `string` | 是 | ID of the snapshot to rollback to |

### RollbackResponse

- 类型: `object`
- 描述: Schema for rollback response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `snapshot_id` | `string` | 是 |  |
| `target_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 |  |
| `target_id` | `string` | 是 |  |
| `rolled_back_at` | `string` | 是 |  |
| `message` | `string` | 是 | Confirmation message about the rollback operation |

### SceneCreate

- 类型: `object`
- 描述: Schema for creating a scene.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scene_order` | `integer` | 是 |  |
| `pov_character_id` | `string \| null` | 否 |  |
| `location` | `string \| null` | 否 |  |
| `content` | `string \| null` | 否 |  |
| `meta` | `object` | 否 |  |
| `chapter_id` | `string` | 是 |  |

### SceneResponse

- 类型: `object`
- 描述: Schema for scene response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scene_order` | `integer` | 是 |  |
| `pov_character_id` | `string \| null` | 否 |  |
| `location` | `string \| null` | 否 |  |
| `content` | `string \| null` | 否 |  |
| `meta` | `object` | 否 |  |
| `id` | `string` | 是 |  |
| `chapter_id` | `string` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### SceneUpdate

- 类型: `object`
- 描述: Schema for updating a scene.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scene_order` | `integer \| null` | 否 |  |
| `pov_character_id` | `string \| null` | 否 |  |
| `location` | `string \| null` | 否 |  |
| `content` | `string \| null` | 否 |  |
| `meta` | `object \| null` | 否 |  |

### SnapshotCreate

- 类型: `object`
- 描述: Schema for creating a snapshot.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 | Type of the target object |
| `target_id` | `string` | 是 | ID of the target object |
| `data` | `object` | 是 | JSON representation of the object state |
| `project_id` | `string` | 是 | Project ID this snapshot belongs to |

### SnapshotResponse

- 类型: `object`
- 描述: Schema for snapshot response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | `string(project, character, world_setting, volume, chapter, scene, suggestion)` | 是 | Type of the target object |
| `target_id` | `string` | 是 | ID of the target object |
| `data` | `object` | 是 | JSON representation of the object state |
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### SnapshotUpdate

- 类型: `object`
- 描述: Schema for updating a snapshot.<br><br>Note: Only data can be updated via PATCH (for corrections).

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `data` | `object \| null` | 否 |  |

### SuggestionActionRequest

- 类型: `object`
- 描述: Schema for suggestion actions (confirm, discard, commit).

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `action` | `string(confirm, discard, commit)` | 是 | Action to perform: confirm, discard, or commit |
| `impact_analysis` | `object \| null` | 否 | Impact analysis results (required for commit) |

### SuggestionActionResult

- 类型: `object`
- 描述: Schema for action result.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `success` | `boolean` | 是 |  |
| `message` | `string` | 是 |  |
| `suggestion_id` | `string` | 是 |  |
| `action` | `string(confirm, discard, commit)` | 是 |  |

### SuggestionCreate

- 类型: `object`
- 描述: Schema for creating a suggestion.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | `string(project, character, world_setting, volume, chapter, scene)` | 是 | Type of target object |
| `target_id` | `string` | 是 | ID of the target object |
| `type` | `string(character_edit, world_edit, chapter_edit, scene_edit, content_gen, outline_gen, continuity_fix)` | 是 | Type of suggestion |
| `content` | `object` | 是 | Suggestion content (JSON) |
| `project_id` | `string` | 是 |  |
| `status` | `string(draft, patched, committed, discarded)` | 否 |  |

### SuggestionResponse

- 类型: `object`
- 描述: Schema for suggestion response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | `string(project, character, world_setting, volume, chapter, scene)` | 是 | Type of target object |
| `target_id` | `string` | 是 | ID of the target object |
| `type` | `string(character_edit, world_edit, chapter_edit, scene_edit, content_gen, outline_gen, continuity_fix)` | 是 | Type of suggestion |
| `content` | `object` | 是 | Suggestion content (JSON) |
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `status` | `string(draft, patched, committed, discarded)` | 是 |  |
| `impact_analysis` | `object \| null` | 是 |  |
| `committed_at` | `string \| null` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### SuggestionUpdate

- 类型: `object`
- 描述: Schema for updating a suggestion.<br><br>Note: Only 'content' can be updated via PATCH. Status changes must go through<br>the confirm/discard/commit actions to ensure proper state transitions.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `content` | `object \| null` | 否 |  |

### ValidationError

- 类型: `object`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `loc` | `array<string \| integer>` | 是 |  |
| `msg` | `string` | 是 |  |
| `type` | `string` | 是 |  |
| `input` | `-` | 否 |  |
| `ctx` | `object` | 否 |  |

### VectorSearchRequest

- 类型: `object`
- 描述: Schema for vector similarity search request.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `query_embedding` | `array<number>` | 是 | Query vector embedding for similarity search |
| `limit` | `integer` | 否 | Maximum number of results to return |
| `threshold` | `number` | 否 | Minimum similarity threshold (cosine) |
| `memory_type` | `string \| null` | 否 | Optional filter by memory type |

### VectorSearchResponse

- 类型: `object`
- 描述: Schema for vector search response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `matches` | `array<MemoryMatch>` | 是 |  |
| `total_count` | `integer` | 是 |  |
| `search_summary` | `string \| null` | 否 |  |

### VolumeCreate

- 类型: `object`
- 描述: Schema for creating a volume.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `volume_number` | `integer \| null` | 否 |  |
| `title` | `string \| null` | 否 |  |
| `outline` | `string \| null` | 否 | 卷细纲总述 |
| `notes` | `string \| null` | 否 |  |
| `project_id` | `string` | 是 |  |

### VolumeResponse

- 类型: `object`
- 描述: Schema for volume response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `volume_number` | `integer \| null` | 否 |  |
| `title` | `string \| null` | 否 |  |
| `outline` | `string \| null` | 否 | 卷细纲总述 |
| `notes` | `string \| null` | 否 |  |
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### VolumeUpdate

- 类型: `object`
- 描述: Schema for updating a volume.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `volume_number` | `integer \| null` | 否 |  |
| `title` | `string \| null` | 否 |  |
| `outline` | `string \| null` | 否 | 卷细纲总述 |
| `notes` | `string \| null` | 否 |  |

### WorldSettingCreate

- 类型: `object`
- 描述: Schema for creating a world setting.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `category` | `string(magic_system, geography, history, organization, technology, culture, religion, economy, rules, other)` | 是 |  |
| `name` | `string` | 是 |  |
| `content` | `string \| null` | 否 |  |
| `meta` | `object` | 否 |  |
| `project_id` | `string` | 是 |  |

### WorldSettingResponse

- 类型: `object`
- 描述: Schema for world setting response.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `category` | `string(magic_system, geography, history, organization, technology, culture, religion, economy, rules, other)` | 是 |  |
| `name` | `string` | 是 |  |
| `content` | `string \| null` | 否 |  |
| `meta` | `object` | 否 |  |
| `id` | `string` | 是 |  |
| `project_id` | `string` | 是 |  |
| `created_at` | `string` | 是 |  |
| `updated_at` | `string` | 是 |  |

### WorldSettingUpdate

- 类型: `object`
- 描述: Schema for updating a world setting.

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `category` | `string(magic_system, geography, history, organization, technology, culture, religion, economy, rules, other) \| null` | 否 |  |
| `name` | `string \| null` | 否 |  |
| `content` | `string \| null` | 否 |  |
| `meta` | `object \| null` | 否 |  |
