# AI 超长篇小说写作 Agent - 实施计划

## 文档信息
- 项目名称：AI 超长篇小说写作 Agent 应用
- 文档类型：实施计划（IMPLEMENTATION_PLAN）
- 版本：v2.0
- 状态：MVP 已完成
- 创建日期：2026-03-12
- 更新日期：2026-03-14

---

## 1. 总体规划

### 1.1 时间线概览

| 阶段 | 时长 | 目标 | 交付物 | 状态 |
|------|------|------|--------|------|
| **Phase 1** | 2 周 | 后端骨架 + 数据模型 | 可运行的后端 API | ✅ 已完成 |
| **Phase 2** | 2 周 | 前端骨架 + 基础 UI | 可访问的前端页面 | ✅ 已完成 |
| **Phase 3** | 2 周 | 核心对象 CRUD | 完整的对象管理功能 | ✅ 已完成 |
| **Phase 4** | 2 周 | Agent 框架 + 对话 | 可用的 AI 写作助手 | ✅ 已完成 |
| **Phase 5** | 2 周 | 三态机制 + 影响分析 | Suggestion 完整流程 | ✅ 已完成 |
| **Phase 6** | 1 周 | 记忆 + 连续性检查 | 基础智能功能 | ✅ 已完成 |
| **Phase 7** | 1 周 | 导出 + 测试 + 文档 | MVP 发布 | ✅ 已完成 |

---

## 2. Phase 1：后端骨架 ✅

### 已完成内容
- [x] 后端项目结构（FastAPI + SQLAlchemy 2.0）
- [x] 配置 requirements.txt
- [x] Docker Compose 配置
- [x] 全部 SQLAlchemy 模型：Project, Character, WorldSetting, Volume, Chapter, Scene, Suggestion, Snapshot, Memory, Dependency
- [x] 数据库会话工厂（支持 PostgreSQL + SQLite）
- [x] Pydantic Schemas（所有模型的 Create/Update/Response）
- [x] 依赖注入（deps.py）
- [x] 健康检查端点
- [x] 全局异常处理
- [x] 配置管理（config.py + pydantic-settings）

---

## 3. Phase 2：前端骨架 ✅

### 已完成内容
- [x] Next.js 15 项目（App Router）
- [x] TypeScript + ESLint + Tailwind CSS
- [x] 通用组件：Button, Input, Modal, Card, Loading
- [x] Zustand 状态管理（projectStore）
- [x] API 客户端封装（fetchApi + 错误处理）
- [x] 21 个页面路由（项目/人物/世界观/章节/场景的 CRUD 页面）

---

## 4. Phase 3：核心对象 CRUD ✅

### 已完成内容
- [x] 后端 68 个 API 端点（全部 CRUD + 特殊操作）
- [x] Service 层（CRUDBase + 各模型特化服务）
- [x] 前端 20 个页面（列表/详情/新建/编辑）
- [x] Suggestion 三态 API（confirm/discard/commit）
- [x] Dependency 影响分析 API
- [x] Memory 向量搜索 API
- [x] Snapshot 快照与回滚 API
- [x] LLM Service（OpenAI SDK 兼容，重试，流式）

---

## 5. Phase 4：Agent 框架 + 对话 ✅

### 已完成内容

**后端 Agent 层**
- [x] `backend/app/agents/base.py` - AgentContext/AgentResult/BaseAgent 抽象类
  - `_call_llm()` 普通调用
  - `_call_llm_stream()` 流式调用
  - `_parse_json_from_response()` JSON 提取
- [x] `backend/app/agents/lore_agent.py` - 世界观助手（world_edit suggestions）
- [x] `backend/app/agents/character_agent.py` - 人物助手（character_edit suggestions）
- [x] `backend/app/agents/outline_agent.py` - 大纲助手（outline_gen/chapter_edit）
- [x] `backend/app/agents/draft_agent.py` - 写作助手（content_gen/scene_edit）
- [x] `backend/app/agents/continuity_agent.py` - 连续性检查（continuity_fix）

**WritingOrchestrator**
- [x] `backend/app/agents/orchestrator.py`
  - LLM 意图分类路由
  - 上下文加载（project, characters, world_settings, chapters, memories）
  - Agent 调用 + Suggestion 自动创建
  - SSE 流式输出
  - auto_summarize()（LLM 摘要 + 事实抽取 + 向量嵌入）
  - continuity_check()

**Agent API**
- [x] `backend/app/schemas/agent.py` - AgentChatRequest/Response, AutoSummarize, ContinuityCheck
- [x] `backend/app/api/v1/agent.py` - 4 个端点：
  - `POST /api/v1/agent/chat` - 对话
  - `POST /api/v1/agent/chat/stream` - SSE 流式对话
  - `POST /api/v1/agent/auto-summarize` - 自动摘要
  - `POST /api/v1/agent/continuity-check` - 连续性检查

**前端 Chat**
- [x] `frontend/lib/stores/chatStore.ts` - Zustand chat store（含流式）
- [x] `frontend/components/AgentChatPanel.tsx` - 浮动聊天面板
- [x] `frontend/components/SuggestionCard.tsx` - 建议卡片（接受/拒绝）
- [x] `frontend/lib/api-client.ts` - agentApi, suggestionApi, exportApi
- [x] `frontend/lib/types.ts` - Suggestion, ChatMessage, AgentChatRequest/Response

---

## 6. Phase 5：三态机制 + UI ✅

### 已完成内容

**三态 UI 组件**
- [x] `frontend/components/SuggestionList.tsx` - 待处理建议列表
- [x] `frontend/components/DiffPreview.tsx` - 修改前后对比
- [x] `frontend/components/ImpactAnalysis.tsx` - 影响范围展示

**页面集成**
- [x] 项目详情页 - AgentChatPanel + SuggestionList
- [x] 人物详情页 - AgentChatPanel（with character context）
- [x] 章节详情页 - AgentChatPanel（with chapter context）
- [x] 场景详情页 - AgentChatPanel（with scene context）

---

## 7. Phase 6：记忆 + 连续性检查 ✅

### 已完成内容
- [x] orchestrator.auto_summarize() - LLM 提取事实 + 向量嵌入存储
- [x] orchestrator.continuity_check() - 加载全项目上下文 + ContinuityAgent 检查
- [x] `POST /api/v1/agent/auto-summarize` API
- [x] `POST /api/v1/agent/continuity-check` API
- [x] 前端章节编辑页保存后自动触发 autoSummarize

---

## 8. Phase 7：导出 + 文档 ✅

### 已完成内容
- [x] `backend/app/services/export.py` - ExportService（TXT + Markdown）
- [x] `backend/app/api/v1/export.py` - `GET /api/v1/projects/{id}/export?format=txt|markdown`
- [x] 前端导出按钮（项目详情页 → 导出 TXT / 导出 Markdown）
- [x] 实施计划文档更新

---

## 9. 当前项目结构

### 后端 (`backend/app/`)
```
app/
├── agents/                    # AI Agent 层
│   ├── base.py               # AgentContext, AgentResult, BaseAgent
│   ├── lore_agent.py         # 世界观助手
│   ├── character_agent.py    # 人物助手
│   ├── outline_agent.py      # 大纲助手
│   ├── draft_agent.py        # 写作助手
│   ├── continuity_agent.py   # 连续性检查
│   └── orchestrator.py       # WritingOrchestrator（路由+上下文+建议）
├── api/v1/                    # API 路由
│   ├── agent.py              # Agent 对话/摘要/检查
│   ├── export.py             # 导出
│   ├── projects.py           # 项目 CRUD
│   ├── characters.py         # 人物 CRUD
│   ├── world_settings.py     # 世界观 CRUD
│   ├── chapters.py           # 章节/卷/场景 CRUD
│   ├── suggestions.py        # 建议三态
│   ├── dependencies.py       # 依赖/影响分析
│   ├── memories.py           # 记忆/向量搜索
│   └── snapshots.py          # 快照/回滚
├── models/                    # 10 个 SQLAlchemy 模型
├── schemas/                   # Pydantic schemas
├── services/                  # 业务逻辑层
│   ├── llm.py                # OpenAI LLM 服务
│   ├── export.py             # 导出服务
│   └── ...                   # 各模型 CRUD 服务
├── core/                      # 配置/异常
└── db/                        # 数据库会话
```

### 前端 (`frontend/`)
```
frontend/
├── app/                       # 21 个页面路由
│   ├── projects/[id]/        # 项目详情 + AI 建议 + 导出
│   │   ├── characters/       # 人物管理 + AI Chat
│   │   ├── chapters/         # 章节管理 + AI Chat
│   │   │   └── scenes/       # 场景管理 + AI Chat
│   │   └── worldsettings/    # 世界观管理
│   └── ...
├── components/
│   ├── AgentChatPanel.tsx    # 浮动 AI 对话面板
│   ├── SuggestionCard.tsx    # 建议卡片
│   ├── SuggestionList.tsx    # 建议列表
│   ├── DiffPreview.tsx       # Diff 对比
│   ├── ImpactAnalysis.tsx    # 影响分析
│   └── ui/                   # Button, Card, Input, Loading, Modal
├── lib/
│   ├── api-client.ts         # API 客户端（含 agentApi, suggestionApi, exportApi）
│   ├── types.ts              # TypeScript 类型定义
│   └── stores/
│       ├── projectStore.ts   # 项目状态
│       └── chatStore.ts      # 聊天状态（含流式）
```

---

## 10. MVP 验证方式

1. **后端测试**: `cd backend && python3 -m pytest tests/` - 已有 35+ 测试文件
2. **前端构建**: `cd frontend && next build` - 21 个页面全部编译通过
3. **端到端流程**: 启动后端 → 前端 → 创建项目 → 打开聊天面板 → 发送消息 → 查看 AI 回复和建议
4. **导出测试**: 创建项目+章节 → 点击导出按钮 → 验证下载文件内容

---

## 11. 后续规划

### V2 计划
- GraphRAG 高级检索
- TipTap 富文本编辑器集成
- React Flow 知识图谱可视化
- 复杂影响分析可视化
- 人物弧光追踪器
- 时间线视图

### V3 计划
- 多用户协作
- 实时协同编辑（Y.js）
- 文风克隆
- 跨媒介资产转换
