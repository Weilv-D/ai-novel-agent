# AI Novel Agent - 项目进度

## 已完成 (Phase 1 进行中)

### 文档修正
- [x] 修正 MVP 工期不一致 (10 周 -> 12 周)
- [x] 统一命名规范: WorldSetting (模型) / world_settings (API/表)
- [x] 明确 MVP 边界: 包含简化版 API Key 认证和快照回滚

### Phase 1: 后端骨架 (Week 1-2)
- [x] 项目结构创建
- [x] pyproject.toml 配置
- [x] 核心配置模块 (config, logging, security)
- [x] 数据库会话工厂
- [x] 所有 SQLAlchemy 模型定义
  - User, Project, Character, WorldSetting
  - Volume, Chapter, Scene
  - Suggestion, Memory, Snapshot, Dependency
- [x] Pydantic Schemas (health, project, character, world_setting, chapter, scene, suggestion, memory, snapshot, dependency)
- [x] FastAPI main.py 入口
- [x] API 路由结构 + health check endpoint (无数据库依赖)
- [x] Alembic 迁移配置
- [x] 初始 Alembic 迁移脚本 (所有表结构)
- [x] 基础测试配置 (使用 SQLite，无外部依赖)
- [x] Health check 测试通过

### 待办 (Phase 1 剩余)
- [x] Docker Compose 本地开发配置 (已存在于 infra/docker-compose.yml)
- [x] LLM Service 基础封装 (带重试、auto-embed、falsy 值正确处理)
- [ ] 环境依赖安装验证 (需 Python 3.11+ + pip/venv 或 Docker)
- [ ] 启动并验证所有服务 (需 Docker 或本地 PostgreSQL)

### Phase 1 新增 API 功能
- [x] Memory API - 叙事事实存储与向量相似度搜索
  - 模型: Memory (支持 pgvector/SQLite 双模式)
  - Schema: MemoryCreate, MemoryResponse, MemorySearchRequest
  - 服务: 向量搜索、语义检索、事实查询
  - API: POST /memories, GET /memories, GET /memories/search, DELETE /memories/{id}
  - 测试: schemas (✓), services (✓), API (✓)

- [x] Snapshot API - 版本控制与回滚
  - 模型: Snapshot
  - Schema: SnapshotCreate, SnapshotResponse
  - 服务: 创建快照、获取快照列表、回滚到指定快照
  - API: POST /snapshots, GET /snapshots, POST /snapshots/{id}/rollback
  - 测试: schemas (✓), services (✓), API (✓)

- [x] Dependency API - 影响分析与关系追踪
  - 模型: Dependency
  - Schema: DependencyCreate, DependencyResponse, DependencyAnalysis
  - 服务: 创建依赖、获取依赖图、影响分析
  - API: POST /dependencies, GET /dependencies, GET /dependencies/analysis
  - 测试: schemas (✓), services (✓), API (✓)

- [x] LLM Service - OpenAI API 封装
  - 服务: generate, embed, embed_single, health_check
  - 重试逻辑: RateLimitError/APIError 自动重试 3 次
  - 参数处理: is not None 检查保留 falsy 值 (temperature=0.0, max_tokens=0)
  - API Key 验证: BadRequestException (400) 当未配置
  - 测试: 23 tests (初始化、生成、嵌入、重试、健康检查)

## 下一步 (Phase 2)

### 前端进度
- [x] Next.js 15 + TypeScript 项目初始化
- [x] App Router 结构 (app/layout.tsx, app/page.tsx)
- [x] Tailwind CSS 配置
- [x] ESLint 配置 (TypeScript + Core Web Vitals)
- [x] 基础 UI 组件 (Card, Button, LoadingSpinner, Input, Textarea, Modal)
- [x] 状态管理 (Zustand)
- [x] API 客户端封装 (lib/api-client.ts，支持空响应处理)
- [x] TypeScript 类型定义 (lib/types.ts)

### 项目管理 (Projects)
- [x] 项目列表页面 (/projects)
- [x] 项目详情页面 (/projects/[id])
- [x] 项目创建页面 (/projects/new)
- [x] 项目编辑页面 (/projects/[id]/edit)
- [x] 项目删除功能 (带确认对话框)

### 章节管理 (Chapters)
- [x] 章节列表页面 (/projects/[id]/chapters)
- [x] 章节详情页面 (/projects/[id]/chapters/[chapterId])
- [x] 章节创建页面 (/projects/[id]/chapters/new)
- [x] 章节编辑页面 (/projects/[id]/chapters/[chapterId]/edit)
- [x] 章节删除功能 (带确认对话框)
- [x] 章节详情页场景列表展示

### 场景管理 (Scenes)
- [x] 场景详情页面 (/projects/[id]/chapters/[chapterId]/scenes/[sceneId])
- [x] 场景创建页面 (/projects/[id]/chapters/[chapterId]/scenes/new)
- [x] 场景编辑页面 (/projects/[id]/chapters/[chapterId]/scenes/[sceneId]/edit)
- [x] 场景删除功能 (带确认对话框)
- [x] 场景内容编辑（富文本域）

### 待办
- [ ] 人物管理页面 (Characters CRUD)
- [ ] 世界观管理页面 (WorldSettings CRUD)

## 项目结构
```
ai-novel-agent/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API 路由
│   │   ├── core/            # 配置、日志、安全
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # 业务逻辑 (待实现)
│   │   ├── agents/          # Agent 编排 (待实现)
│   │   ├── db/              # 数据库会话
│   │   └── main.py          # FastAPI 入口
│   ├── tests/               # 测试
│   ├── alembic/             # 数据库迁移
│   ├── scripts/             # 工具脚本
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                # Next.js 15 + TypeScript
│   ├── app/               # App Router pages
│   ├── public/            # 静态资源
│   ├── package.json       # 依赖配置
│   └── tsconfig.json       # TypeScript 配置
├── infra/
│   └── docker-compose.yml   # 本地开发
└── docs/                    # PRD, TECH_ARCH, MVP_SCOPE, IMPLEMENTATION_PLAN
```

## 关键决策
- 后端: FastAPI + SQLAlchemy 2.0 (async)
- 数据库: PostgreSQL 16 + pgvector
- 向量存储: MVP 使用 pgvector (V2 迁移到 Qdrant)
- 认证: MVP 简化为 API Key (无复杂权限)

## 数据库兼容性

### SQLite 测试支持
项目支持 SQLite 进行本地测试和开发，无需运行 PostgreSQL：

- **测试**: 使用 `sqlite+aiosqlite:///:memory:` 运行单元测试
- **Alembic 迁移**: 方言感知，自动适配 PostgreSQL 和 SQLite
  - PostgreSQL: `UUID`, `JSON` (JSONB), `now()`
  - SQLite: `String(36)`, `JSON` (TEXT), `CURRENT_TIMESTAMP`
- **向量搜索**: PostgreSQL 使用 pgvector，SQLite 回退到 TEXT 存储

### 验证 SQLite 兼容性
```bash
# 运行 SQLite 迁移测试
python backend/scripts/test_sqlite_migration.py

# 或直接运行测试套件
cd backend && python -m pytest tests/
```

**注意**: 生产环境必须使用 PostgreSQL 16 + pgvector。SQLite 仅用于测试和快速本地开发。
