# 当前技术实现

最后更新：2026-03-16

## 文档定位

本文档描述仓库当前已经落地的真实实现，重点回答三类问题：

- 系统现在如何运行
- 代码按什么层次组织
- 当前交付边界在哪里

如果你要查看：

- 使用方式：见 [README.md](../README.md)
- 开发环境：见 [DEVELOPMENT.md](DEVELOPMENT.md)
- 目标架构：见 [TECH_ARCH.md](TECH_ARCH.md)
- 演进计划：见 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
- 项目状态：见 [STATUS.md](STATUS.md)

## 系统定位

当前系统是一个独立实例运行的 Agent 化小说工作台。它不是通用协作平台，也不是只返回建议文本的聊天助手。主流程目标是：

- 用项目化数据结构承载长篇创作
- 用 Agent Workspace 承载创作与修改指令
- 用 preview-first 流程控制写入
- 用 verification gate 保障计划与落库一致
- 用 checkpoint compact flow 管理长期线程

## 运行拓扑

系统采用前后端分离的单体部署形态：

- 前端：Next.js 15 App Router + React 19
- 后端：FastAPI + SQLAlchemy 2.0 (async)
- 数据层：PostgreSQL + pgvector
- 运行依赖：Redis
- 模型接口：OpenAI 兼容 LLM / Embedding API

请求流向：

1. 前端工作台发起 CRUD、Agent 线程消息、确认执行等请求。
2. 后端 API 路由进入 service 层。
3. service 层调用 CRUD、workflow、risk、skill、snapshot、memory、export 等实现。
4. PostgreSQL 持久化主数据与 Agent 运行数据。
5. Redis 提供运行期依赖与健康检查目标。

## 代码分层

### 后端

- `app/api/v1/`：HTTP 路由和依赖注入
- `app/services/`：业务编排与 Agent 主实现
- `app/models/`：SQLAlchemy 模型
- `app/schemas/`：Pydantic contract
- `app/core/`：配置，安全，日志
- `app/db/`：会话、初始化、迁移入口
- `app/agent_skills/`：通用 skill
- `app/agent_profiles/`：profile 覆盖

### 前端

- `frontend/app/`：页面路由
- `frontend/components/`：工作台与对象页组件
- `frontend/lib/`：类型、API client、展示元数据和 store
- `frontend/components/ui/`：基础 UI 组件

项目详情页内的 `AgentWorkspace.tsx` 是前端主工作台。

## 数据模型

### 创作对象

| 模型 | 主要字段 |
|------|----------|
| `Project` | id, name, genre, target_audience, target_word_count, status, summary, notes, agent_profile_id, meta |
| `Character` | id, project_id, name, role, profile, relationships, arc_state, notes |
| `WorldSetting` | id, project_id, category, name, content, meta |
| `Volume` | id, project_id, volume_number, title, outline, notes |
| `Chapter` | id, project_id, volume_id, chapter_number, title, outline, content, status, notes |
| `Scene` | id, chapter_id, scene_order, pov_character_id, location, content, meta |

### Agent 工作流对象

| 模型 | 主要字段 |
|------|----------|
| `AgentThread` | id, project_id, title, is_default, meta |
| `AgentMessage` | id, thread_id, role, content, meta |
| `AgentRun` | id, thread_id, project_id, status, summary, risk_summary, execution_contract, verification_status |
| `AgentOperation` | id, run_id, position, tool_name, target_type, target_id, description, payload, preview, status |
| `AgentSubtask` | id, run_id, position, role, title, status, summary, child_trace |
| `AgentThreadCheckpoint` | id, thread_id, profile_id, thread_summary, active_object_bundle, recent_run_digest |

### 一致性与回溯对象

| 模型 | 用途 |
|------|------|
| `Snapshot` | 对象状态快照，用于回溯和版本管理 |
| `Dependency` | 对象间依赖关系 |
| `Suggestion` | 创作建议 |

### 检索对象

| 模型 | 主要字段 |
|------|----------|
| `Memory` | id, project_id, memory_type, content, embedding, meta |

当前系统不维护 `User` 实体，也不为 `Project` 绑定 owner。

## Agent 工作流

当前 Agent 主流程稳定在项目级 `thread / run / operation`。

### 线程

每个项目有一个默认 `AgentThread`，它承载该项目的长期上下文。

### 消息

用户发送消息后，系统先写入 `AgentMessage`，然后进入规划流程。

### 规划

规划由 `app/services/agent_workflow.py` 驱动，主要步骤为：

1. 读取项目级 profile
2. 加载 profile-aware skill bundle
3. 装配项目上下文和焦点对象
4. 装配 checkpoint、planner window 和 retained window
5. 生成 planner 输出
6. 组装用户可见 operations 与内部 subtasks
7. 分类风险、装配 execution contract
8. 返回待确认的 `AgentRun`

### 执行

确认前，run 不会写入主对象。确认后：

1. 进入执行态
2. 为目标对象创建 snapshot
3. 复用 CRUD service 执行写入
4. 更新 operation 与 capability execution record
5. 进入 verification gate
6. 通过后标记 `completed`

## 内部执行层

当前内部角色包括：

- `planner`：规划器
- `researcher`：研究员
- `writer`：写作者
- `editor`：编辑者
- `continuity`：连续性检查
- `executor`：执行器

这些角色已经具备：

- child unit contract
- subtask trace
- recovery boundary
- hook trace

它们仍属于 workflow 内部执行层，不是独立 child session。

## Profile 与 Skill

当前 skill 系统是项目级 profile-aware 设计。

### 已实现

- `Project.meta.agent_profile_id`（实际存储在 `agent_profile_id` 字段）
- 内置 `default`
- 内置 `xianxia_intrigue`
- `AGENT_SKILLS_DIR` profile 根目录覆盖
- 运行期可见的 profile / skill catalog

### 规范源

`xianxia_intrigue` 直接使用 `others/` 中的提示词作为规范源，并以文件化 skill 暴露给 planner 和 operation。

## Contract 设计

当前后端已经把核心运行状态稳定成显式响应字段。

### Execution Contract

```json
{
  "registry_version": "string",
  "phases": [
    {
      "phase": "plan | build",
      "mode": "restricted | gated",
      "allowed_permission_levels": ["read_search", "standard_write", "high_risk_write"],
      "tool_scope": ["..."],
      "role_scope": ["planner", "researcher", "writer", "editor", "continuity"],
      "confirmation_gate": "none | single | double",
      "requires_confirmation": false,
      "requires_secondary_confirmation": false,
      "operation_count": 0,
      "child_units": [...],
      "capabilities": [...]
    }
  ]
}
```

### Risk Contract

```json
{
  "policy_version": "string",
  "overall_risk_level": "low | medium | high",
  "confirmation_gate": "none | single | double",
  "requires_confirmation": true,
  "requires_secondary_confirmation": false,
  "total_operations": 1,
  "low_risk_operation_count": 1,
  "medium_risk_operation_count": 0,
  "high_risk_operation_count": 0,
  "high_risk_operation_positions": [],
  "secondary_confirmation_operation_positions": [],
  "applied_policies": [...],
  "summary": "string"
}
```

### Verification Contract

- verification_status: `pending | passed | failed | skipped`
- verification_summary: 详细验证结果
- operation execution_result: 每个操作的执行结果

### Compact Contract

- compact_policy: 压缩策略配置
- planner_window: 规划器窗口
- retained_window: 保留窗口
- active_bundle_contract: 活跃数据包契约
- compaction_boundary: 压缩边界

前端和测试都直接消费这些字段，不需要再从非结构化 `meta` 反推状态。

## Verification Gate

当前 verification 不是单一 hash 比对，而是多层校验。

### 已实现的校验层

- 字段级校验
- snapshot linkage 校验
- snapshot-derived semantic 校验
- content transition 校验
- domain-level semantic 校验

### Domain Verification 覆盖的业务语义

#### Character

| 规则 ID | 描述 |
|---------|------|
| `character_name_empty` | 名称不能为空 |
| `character_name_duplicate` | 同项目下名称唯一 |
| `character_age_invalid` | 年龄必须为非负整数 |

#### WorldSetting

| 规则 ID | 描述 |
|---------|------|
| `world_setting_name_empty` | 名称不能为空 |
| `world_setting_content_empty` | 内容不能为空 |
| `world_setting_name_duplicate` | 同分类下名称唯一 |

#### Chapter/Scene

| 规则 ID | 描述 |
|---------|------|
| 章节序号唯一 | 同项目内 chapter_number 唯一 |
| 场景序号唯一 | 同章节内 scene_order 唯一 |
| 卷归属 | volume_id 必须属于同一项目 |
| POV 人物归属 | pov_character_id 必须属于同一项目 |

## E2E 测试基础设施

系统已集成 Playwright 作为浏览器级测试框架。

### 核心组件

- `playwright.config.ts`：Playwright 配置
- `e2e/e2e.spec.ts`：E2E 测试用例
- `e2e/fixtures/test-helpers.ts`：测试辅助函数
- `e2e/fixtures/planner-responses.json`：Fixture planner 响应数据

### Fixture Planner 模式

通过环境变量启用测试专用的 planner 模式：

- `AGENT_E2E_MODE=fixture`：启用 fixture 模式
- `AGENT_E2E_FIXTURE_PATH`：指定 fixture 文件路径

在 fixture 模式下，系统按消息全文精确匹配返回固定 planner 输出，不调用真实 LLM。

### 前端测试标识

关键 UI 节点添加了 `data-testid` 属性：

- 首页：API key 输入与保存按钮
- 新建项目：表单提交按钮
- Agent Workspace：输入框、发送按钮、确认按钮、二次确认按钮
- 项目详情页：导出按钮
- 项目列表页：导入入口和上传确认按钮

## Agent 流式事件系统

系统支持实时显示 Agent 思考过程与执行状态，通过 Server-Sent Events (SSE) 实现。

### 事件类型

| 类型 | 阶段 | 说明 |
|------|------|------|
| `status` | init, load_context, compact_check, prepare_operations, risk_assessment | 状态更新 |
| `thinking` | planning, plan_complete | Agent 思考过程 |
| `operation_progress` | prepare | 操作准备进度 |
| `verification` | - | 验证结果 |
| `message_chunk` | assistant_message | 助手消息分块 |
| `result` | complete | 最终执行结果 |
| `error` | - | 错误信息 |

### 流式接口

```
POST /api/v1/agent/threads/{thread_id}/messages
Content-Type: application/json

{
  "content": "创建一个人物",
  "context": {},
  "stream": true
}
```

响应使用 SSE 格式：

```
data: {"type": "status", "stage": "init", "message": "正在初始化 Agent 工作流...", "timestamp": "...", "detail": {}}

data: {"type": "thinking", "stage": "planning", "message": "Agent 正在分析您的请求并规划操作...", "detail": {...}}

data: {"type": "thinking", "stage": "plan_complete", "message": "规划完成，共 1 个操作", "detail": {...}}

data: {"type": "result", "stage": "complete", "message": "Agent 规划完成，等待用户确认", "detail": {...}}

data: [DONE]
```

### 前端实时显示

`AgentWorkspace.tsx` 组件在流式请求期间显示实时事件面板：

- 思考中状态指示器（脉冲动画）
- 当前处理阶段显示
- 操作列表预览
- 错误信息展示

### 事件流程

```
用户发送消息
    ↓
[status:init] 初始化
    ↓
[status:load_context] 加载项目上下文
    ↓
[status:compact_check] 压缩检查
    ↓
[thinking:planning] 分析请求并规划
    ↓
[thinking:plan_complete] 规划完成
    ↓
[status:prepare_operations] 准备操作预览
    ↓
[operation_progress] 逐个准备操作
    ↓
[status:risk_assessment] 风险评估
    ↓
[result] 等待用户确认
```

## 项目包导出导入

系统支持完整项目数据的打包导出与恢复导入。

### 导出接口

```
GET /api/v1/projects/{project_id}/package
```

导出为 ZIP 文件，包含：

- `manifest.json`：包元信息（版本、导出时间、源项目信息、embedding 维度）
- `project_bundle.json`：完整项目数据

### 导入接口

```
POST /api/v1/projects/import
Content-Type: multipart/form-data
```

导入策略：

- 始终创建新项目副本，不覆盖现有项目
- 单事务内完成，任一步失败整单回滚
- 所有对象重新生成 UUID，并维护旧 ID → 新 ID 映射
- 重写所有引用关系（project_id、volume_id、chapter_id、pov_character_id、dependencies、snapshots）
- `Memory.embedding` 仅在向量维度与当前 EMBEDDING_DIMENSION 一致时保留，否则置空并给出 `requires_reembed` warning

### 导入响应

```json
{
  "project_id": "uuid",
  "project_name": "string",
  "imported_counts": {
    "characters": 5,
    "world_settings": 10,
    "volumes": 2,
    "chapters": 20,
    "scenes": 50,
    "dependencies": 30,
    "snapshots": 100,
    "memories": 15
  },
  "warnings": [
    {
      "code": "embedding_dimension_mismatch",
      "message": "string",
      "details": {}
    }
  ]
}
```

## Compact Flow

长线程通过 checkpoint 压缩上下文。当前 planner 有两种输入模式：

- `recent_window`：使用最近消息窗口
- `checkpoint_delta`：使用检查点增量

checkpoint 当前保存：

- `thread_summary`：线程摘要
- `recent_run_digest`：最近运行摘要
- `active_object_bundle`：活跃对象包
- `profile_id`：配置文件 ID

compact 行为通过以下 contract 对外可见：

- `compact_policy`：压缩策略
- `planner_window`：规划器窗口
- `retained_window`：保留窗口
- `active_bundle_contract`：活跃数据包契约
- `compaction_boundary`：压缩边界

## 用户体验优化

### 状态持久化

用户偏好设置通过 Zustand persist middleware 自动持久化到 localStorage：

| 存储键 | 内容 |
|--------|------|
| `user-preferences` | 主题、字体大小、语言、侧边栏状态等 |
| `form-draft-*` | 表单草稿自动保存 |
| `api_key` | API 认证密钥 |
| `api_key_header` | API Key header 名称 |

### 全局组件

| 组件 | 功能 |
|------|------|
| `GlobalProgressBar` | 页面切换时的顶部进度条 |
| `NetworkStatusIndicator` | 网络断开时的底部提示条 |
| `ToastProvider` | 全局通知系统（成功/错误/警告/信息） |
| `MobileNav` | 移动端底部导航菜单 |
| `PreferencesInit` | 初始化用户偏好设置（主题、字体大小） |

### 骨架屏组件

为提升感知性能，提供多种骨架屏组件：

- `Skeleton` - 基础骨架屏
- `SkeletonText` - 文本占位
- `SkeletonCard` - 卡片占位
- `SkeletonList` - 列表占位
- `SkeletonProjectCard` - 项目卡片占位
- `SkeletonCharacterCard` - 人物卡片占位
- `SkeletonChapterCard` - 章节卡片占位
- `SkeletonAgentWorkspace` - Agent 工作区占位

### 性能优化 Hooks

| Hook | 功能 |
|------|------|
| `useDebounce` | 防抖值 |
| `useDebouncedCallback` | 防抖回调 |
| `useThrottle` | 节流值 |
| `useLocalStorage` | localStorage 状态管理 |
| `useMediaQuery` | 媒体查询响应 |
| `useIsMobile` | 移动端检测 |
| `useIsTablet` | 平板检测 |
| `useIsDesktop` | 桌面端检测 |
| `useOnline` | 网络状态检测 |
| `useIntersectionObserver` | 元素可见性检测 |
| `usePrevious` | 获取前一个值 |

### CSS 优化

- 硬件加速：`transform: translateZ(0)`, `will-change`
- 动画支持：Toast 滑入、按钮加载旋转
- 减少动画模式：`prefers-reduced-motion`
- 触摸设备优化：增大触摸目标、禁用 hover 效果
- 打印样式：隐藏非必要元素

### 无障碍支持

- 语义化 HTML 标签
- ARIA 属性（`role`, `aria-label`, `aria-busy`）
- 键盘导航支持
- 焦点可见性样式（`focus-visible`）

## 前端工作台

当前 `AgentWorkspace` 不是简单聊天框，它承担这些职责：

- 消息历史展示
- run 计划与 diff 预览
- 风险摘要与确认面板
- verification 结果展示
- subtask 与 child trace 展示
- checkpoint 与 compact contract 展示

因此它是执行工作台，而不是对话容器。

## 当前交付边界

当前范围明确排除：

- 多实例协作与组织权限
- 真正独立运行的 child agent session
- 面向公网的完整安全加固

这些边界由产品定位决定，不代表系统内部结构不完整。

## API 端点总览

### 创作对象 API

| 端点前缀 | 功能 |
|----------|------|
| `/api/v1/projects` | 项目 CRUD |
| `/api/v1/characters` | 人物 CRUD |
| `/api/v1/world-settings` | 世界观 CRUD |
| `/api/v1/volumes` | 卷 CRUD |
| `/api/v1/chapters` | 章节 CRUD |
| `/api/v1/scenes` | 场景 CRUD |
| `/api/v1/memories` | 记忆 CRUD + 向量搜索 |
| `/api/v1/suggestions` | 建议 CRUD |
| `/api/v1/dependencies` | 依赖关系 CRUD |
| `/api/v1/snapshots` | 快照 CRUD |

### Agent 工作流 API

| 端点 | 功能 |
|------|------|
| `POST /api/v1/agent/threads` | 创建/获取项目线程 |
| `GET /api/v1/agent/threads/{thread_id}` | 获取线程状态 |
| `POST /api/v1/agent/threads/{thread_id}/messages` | 发送消息（支持流式） |
| `GET /api/v1/agent/runs/{run_id}` | 获取运行状态 |
| `POST /api/v1/agent/runs/{run_id}/confirm` | 确认执行 |
| `POST /api/v1/agent/runs/{run_id}/confirm-high-risk` | 高风险二次确认 |
| `POST /api/v1/agent/runs/{run_id}/cancel` | 取消运行 |
| `GET /api/v1/agent/profiles` | 获取可用配置 |
| `GET /api/v1/agent/capabilities` | 获取能力注册表 |
| `GET /api/v1/agent/risk-policies` | 获取风险策略注册表 |
| `GET /api/v1/agent/skills` | 获取技能目录 |

### 导出/导入 API

| 端点 | 功能 |
|------|------|
| `GET /api/v1/projects/{id}/export` | 导出为 TXT/Markdown |
| `GET /api/v1/projects/{id}/package` | 导出为 ZIP 包 |
| `POST /api/v1/projects/import` | 从 ZIP 包导入 |

### Legacy API

| 端点 | 功能 |
|------|------|
| `POST /api/v1/agent/chat` | 传统聊天接口 |
| `POST /api/v1/agent/chat/stream` | 传统流式聊天 |
| `POST /api/v1/agent/auto-summarize` | 自动摘要 |
| `POST /api/v1/agent/continuity-check` | 连续性检查 |
