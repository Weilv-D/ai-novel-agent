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

### 人物管理 (Characters)
- [x] 人物列表页面 (/projects/[id]/characters)
- [x] 人物详情页面 (/projects/[id]/characters/[characterId])
- [x] 人物创建页面 (/projects/[id]/characters/new)
- [x] 人物编辑页面 (/projects/[id]/characters/[characterId]/edit)
- [x] 人物删除功能 (带确认对话框)

### 世界观管理 (WorldSettings)
- [x] 设定列表页面 (/projects/[id]/worldsettings)
- [x] 设定详情页面 (/projects/[id]/worldsettings/[settingId])
- [x] 设定创建页面 (/projects/[id]/worldsettings/new)
- [x] 设定编辑页面 (/projects/[id]/worldsettings/[settingId]/edit)
- [x] 设定删除功能 (带确认对话框)
- [x] 按分类分组展示

### 待办
- [ ] 运行 docker-compose 并验证所有服务连通性（需 Docker 环境）
- [ ] 前后端集成端到端测试（需运行后端服务）

## 验证记录（区分静态 vs 运行）

### 后端 HTTP 集成测试 - pytest (2026-03-14)
```bash
cd backend && python -m pytest tests/test_integration/test_http_integration.py -v
```
**结果**: 33 passed

**覆盖范围** (端到端 HTTP 测试，使用真实 SQLite 数据库):
- ✓ Health Check (1/1)
- ✓ Projects API (List/Create/Get/Update - 4/4)
- ✓ Characters API (List/Create/Get/Update/Delete - 5/5)
- ✓ Volumes API (List/Create/Get/Update/Delete - 5/5)
- ✓ Chapters API (List/Create/Get/Update/Delete + volume_id 关联 - 7/7)
- ✓ Scenes API (List/Create/Get/Update/Delete - 5/5)
- ✓ WorldSettings API (List/Create/Get/Update/Delete - 5/5)
- ✓ Cleanup (Cascade delete - 1/1)

**测试配置**: SQLite in-memory，ASGI Transport，db_session 依赖注入

**说明**: 后端 HTTP 集成测试全部通过，使用 pytest 框架验证所有核心 API 端点。
测试在隔离的 SQLite 内存数据库上运行，无需 Docker 或 PostgreSQL。
此测试与 verify_sqlite_integration.py 脚本功能等价，但提供更好的 CI 集成。

### 后端单元测试 - SQLite (2026-03-13)
```bash
cd backend && python -m pytest tests/
```
**结果**: 328 passed, 2 skipped, 9 warnings (18.42s)

**覆盖范围** (单元测试):
- ✓ Projects API (CRUD + list)
- ✓ Chapters API (CRUD + list + by_project)
- ✓ Scenes API (CRUD + list + by_chapter)
- ✓ Characters API (CRUD + list + by_project)
- ✓ WorldSettings API (CRUD + list + by_project + by_category)
- ✓ Memory API (CRUD + search + similarity)
- ✓ Snapshot API (CRUD + rollback)
- ✓ Dependency API (CRUD + analysis)
- ✓ Suggestion API (CRUD + state transitions)

**测试配置**: SQLite in-memory (无外部依赖)

**说明**: 后端单元测试全部通过，验证了 service 层和 API 层的逻辑正确性。
后端 HTTP 集成测试已完成（见下文 pytest HTTP 集成测试）。
但未进行前后端联调测试，未验证前端页面与后端 API 的实际连通性。

### 前端构建验证 (2026-03-13)
```bash
cd frontend && npm run build
```
**结果**: ✓ 成功 (20 routes)

**生成的路由**:
- / (首页)
- /projects (项目列表)
- /projects/new (新建项目)
- /projects/[id] (项目详情)
- /projects/[id]/edit (编辑项目)
- /projects/[id]/chapters (章节列表)
- /projects/[id]/chapters/new (新建章节)
- /projects/[id]/chapters/[chapterId] (章节详情)
- /projects/[id]/chapters/[chapterId]/edit (编辑章节)
- /projects/[id]/chapters/[chapterId]/scenes/[sceneId] (场景详情)
- /projects/[id]/chapters/[chapterId]/scenes/new (新建场景)
- /projects/[id]/chapters/[chapterId]/scenes/[sceneId]/edit (编辑场景)
- /projects/[id]/characters (人物列表)
- /projects/[id]/characters/new (新建人物)
- /projects/[id]/characters/[characterId] (人物详情)
- /projects/[id]/characters/[characterId]/edit (编辑人物)
- /projects/[id]/worldsettings (世界观列表)
- /projects/[id]/worldsettings/new (新建设定)
- /projects/[id]/worldsettings/[settingId] (设定详情)
- /projects/[id]/worldsettings/[settingId]/edit (编辑设定)

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

### 后端数据库兼容性修复 (2026-03-13)
- [x] 修复 `init_db.py` 中的 pgvector 扩展创建逻辑
  - 添加数据库方言检测，仅在 PostgreSQL 时创建扩展
  - SQLite 环境跳过扩展创建，避免启动错误
  - `reset_database()` 仅支持 PostgreSQL，其他方言抛出明确错误

### 开发环境配置 - 静态校对 (2026-03-13)
- [x] frontend/Dockerfile - Node 20 Alpine 开发环境
- [x] infra/docker-compose.yml - 添加 frontend 服务配置
  - Backend (8000), Frontend (3000), PostgreSQL (5432), Redis (6379)
  - 卷挂载配置支持实时代码编辑
- [x] infra/start.sh - 启动脚本（语法检查通过）
- [x] backend/scripts/verify_api_integration.py - HTTP 集成验证脚本（已准备，待运行验证）
  - 字段名已与后端 schema 对齐（name, chapter_number, scene_order, profile dict）
  - 路由路径已修正为 flat 结构（/characters, /chapters, /world-settings）
  - 创建请求已添加 project_id 到 request body
  - SceneCreate 已移除不存在的 title 字段
  - Python 语法检查通过

### 运行时集成验证 - 已完成
- [x] SQLAlchemy `.metadata` 命名冲突修复 (2026-03-13)
  - 问题: Pydantic schema 使用 `alias="metadata"` 与 SQLAlchemy DeclarativeBase 的 `.metadata` 属性冲突
  - 修复: 移除所有 schema 中 `meta` 字段的 `alias="metadata"`，使用直接字段名 `meta`
  - 影响范围: project.py, chapter.py (Scene), world_setting.py
  - 验证: 所有 API 返回正确的 `meta:{}` 而非 MetaData 对象
- [x] SQLite HTTP 集成验证 (2026-03-14) - 49/49 测试通过
  - 新增 `scripts/verify_sqlite_integration.py` - 完整 HTTP 集成测试（使用端口 8765）
  - 新增 `scripts/create_test_user.py` - 测试用户创建工具
  - 验证结果 (49 tests):
    - ✅ Health Check (200 OK - 1/1)
    - ✅ Projects API (Create/List/Get/Update - 4/4)
    - ✅ Volumes API (Create/List/Get/Update/Delete - 5/5)
    - ✅ Characters API (Create/List/Get/Update/Delete - 5/5)
    - ✅ Chapters API (Create/List/Get/Update/Delete - 6/6)
    - ✅ Scenes API (Create/List/Get/Update/Delete - 5/5)
    - ✅ WorldSettings API (Create/List/Get/Update/Delete - 5/5)
    - ✅ Memories API (Create/List/Get/Update/Delete - 5/5)
    - ✅ Snapshots API (Create/List/Get/Delete - 4/4)
    - ✅ Suggestions API (Create/List/Get/Discard - 4/4)
    - ✅ Dependencies API (Create/List/Get/Delete - 4/4)
    - ✅ Cleanup (Delete project - 1/1)
  - 测试环境: SQLite 文件数据库，无需 Docker/PostgreSQL
  - 覆盖范围: 所有核心 API 端点已验证（包括 Volume API）
- [ ] Docker/PostgreSQL 环境集成验证（待 Docker 可用）
  - verify_api_integration.py 可验证 PostgreSQL 特有功能 (pgvector)
