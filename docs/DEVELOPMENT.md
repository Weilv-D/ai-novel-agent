# 开发手册

本文档面向仓库维护者，说明本地环境、运行方式、质量门、清理规则和文档分工。

## 工作区约定

当前仓库默认使用这些本地环境：

- `backend/.venv`：后端 Python 虚拟环境
- `frontend/node_modules`：前端依赖目录
- `backend/.env`：后端本地配置
- `frontend/.env.local`：前端本地配置

仓库根目录的 `/.venv` 不参与项目运行。

## 开发模式

仓库当前围绕独立实例模式开发，主要约定如下：

- 不维护 `User` 实体和项目归属用户
- 访问控制保留为实例级 `ADMIN_API_KEY`
- Agent 主流程是 `thread / run / operation`
- 主交互入口是项目详情页内的 `AgentWorkspace`
- 所有结构化写入都走 preview-first、confirm-then-execute
- 长线程通过 checkpoint compact flow 管理上下文

## 后端开发

### 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Python | >= 3.11 |
| PostgreSQL | >= 16 (with pgvector) |
| Redis | >= 7 |

### 初始化

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
```

### 环境变量配置

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| DATABASE_URL | 是 | - | PostgreSQL 连接字符串 |
| REDIS_URL | 否 | redis://localhost:6379 | Redis 连接字符串 |
| OPENAI_API_KEY | 是 | - | OpenAI API 密钥 |
| OPENAI_BASE_URL | 否 | - | OpenAI API 基础 URL（用于兼容 API） |
| OPENAI_MODEL | 否 | gpt-4o | 使用的模型名称 |
| EMBEDDING_MODEL | 否 | text-embedding-3-small | Embedding 模型名称 |
| EMBEDDING_DIMENSION | 否 | 1536 | Embedding 向量维度 |
| ADMIN_API_KEY | 否 | - | 管理员 API 密钥（启用后所有业务接口需要认证） |
| API_KEY_HEADER | 否 | X-API-Key | API Key 请求头名称 |
| AGENT_SKILLS_DIR | 否 | - | Agent Skills 根目录覆盖 |
| AGENT_E2E_MODE | 否 | - | E2E 测试模式（fixture） |
| AGENT_E2E_FIXTURE_PATH | 否 | - | E2E 测试 fixture 文件路径 |

### 常用命令

```bash
# 完整验证
./.venv/bin/python verify.py

# 运行测试
./.venv/bin/python -m pytest

# 运行测试（带覆盖率）
./.venv/bin/python -m pytest --cov=app --cov-report=html

# 代码检查
./.venv/bin/ruff check app tests scripts

# 类型检查
./.venv/bin/python -m mypy app

# 启动开发服务器
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### 运行约定

- 后端命令应在 `backend/` 目录执行，以便 `Settings` 正确解析 `.env`
- shell 环境变量优先级高于 `.env`
- SQLite 仅用于测试和轻量验证；目标运行环境仍是 PostgreSQL + pgvector
- `AGENT_SKILLS_DIR` 是 profile 根目录覆盖入口
- `GET /api/v1/agent/profiles`、`/skills`、`/risk-policies`、`/capabilities` 是运行期排障的第一批接口

## 前端开发

### 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Node.js | >= 18 |
| npm | >= 9 |

### 初始化

```bash
cd frontend
npm install
```

### 环境变量配置

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| NEXT_PUBLIC_API_URL | 否 | http://localhost:8000 | 后端 API 地址 |

### 常用命令

```bash
# 开发模式
npm run dev

# 代码检查
npm run lint

# 构建
npm run build

# 启动生产服务器
npm run start
```

### 运行约定

- Next.js 配置位于 `frontend/next.config.mjs`
- 全局样式入口由 `frontend/app/layout.tsx` 引入 `frontend/app/globals.css`
- 前端脚本通过 `node` 直接调用本地 CLI，不依赖 `node_modules/.bin` 的可执行位
- 页面主入口是 `frontend/app/projects/[id]/page.tsx`
- `frontend/.next-docker` 是 Docker 前端运行目录，不应在服务运行时被删除

## Docker 联调

Docker Compose 提供完整本地环境：

```bash
cd infra
docker compose up -d
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
```

默认访问地址：

| 服务 | 地址 |
|------|------|
| 前端工作台 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/v1/health |
| PostgreSQL | localhost:5433 |
| Redis | localhost:6379 |

### Docker Compose 服务

| 服务 | 说明 |
|------|------|
| postgres | PostgreSQL 16 + pgvector |
| redis | Redis 7 |
| backend | FastAPI 后端 |
| frontend | Next.js 前端 |

## 验证路径

### 仓库级验证

```bash
make verify
```

包含：

- 后端 lint
- 后端类型检查
- 后端测试
- 前端 lint
- 前端构建

### E2E 测试

```bash
make e2e
```

E2E 测试使用 Playwright，运行时会启动隔离的后端（SQLite 临时库）和前端服务。

### 后端独立验证

```bash
make backend-verify
cd backend && ./.venv/bin/python scripts/verify_sqlite_integration.py
cd backend && ./.venv/bin/python scripts/verify_api_integration.py
```

### 快速结构检查

```bash
cd backend
./.venv/bin/python verify.py
```

它覆盖导入、OpenAPI、路由和 Alembic 基本健康度。

## 清理规则

```bash
make clean
```

`make clean` 会清理缓存和临时构建产物，但不会删除：

- `backend/.venv`
- `frontend/node_modules`
- 本地 `.env` 文件
- `frontend/.next-docker`

## 文档分工

| 文档 | 用途 |
|------|------|
| [README.md](../README.md) | 使用者手册 |
| [backend/README.md](../backend/README.md) | 后端运行与结构说明 |
| [TECH_IMPLEMENTATION.md](TECH_IMPLEMENTATION.md) | 当前实现 |
| [TECH_ARCH.md](TECH_ARCH.md) | 目标架构 |
| [STATUS.md](STATUS.md) | 交付状态与边界 |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | 演进计划 |
| [API_REFERENCE.md](API_REFERENCE.md) | API 参考文档 |
| [PRD.md](PRD.md) | 产品需求文档 |

## 测试策略

### 后端测试

| 测试类型 | 目录 | 说明 |
|----------|------|------|
| API 集成测试 | `tests/test_api/` | 测试 API 端点 |
| 服务层单元测试 | `tests/test_services/` | 测试业务逻辑 |
| Schema 验证测试 | `tests/test_schemas/` | 测试 Pydantic 模型 |
| 核心模块测试 | `tests/test_core/` | 测试配置、异常等 |
| 集成测试 | `tests/test_integration/` | 端到端集成测试 |

### 测试配置

- 测试框架：pytest + pytest-asyncio
- 测试数据库：SQLite（隔离测试）
- 覆盖率工具：pytest-cov

### 运行特定测试

```bash
# 运行单个测试文件
./.venv/bin/python -m pytest tests/test_api/test_projects.py -v

# 运行特定测试类
./.venv/bin/python -m pytest tests/test_api/test_projects.py::TestProjects -v

# 运行特定测试方法
./.venv/bin/python -m pytest tests/test_api/test_projects.py::TestProjects::test_create_project -v

# 运行带标记的测试
./.venv/bin/python -m pytest -m "not slow" -v
```

## 常见问题

### 数据库迁移

```bash
# 生成迁移文件
./.venv/bin/alembic revision --autogenerate -m "description"

# 应用迁移
./.venv/bin/alembic upgrade head

# 回滚迁移
./.venv/bin/alembic downgrade -1
```

### 依赖更新

```bash
# 后端依赖更新
cd backend
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -e ".[dev]"

# 前端依赖更新
cd frontend
npm update
```

### 日志调试

后端使用 structlog 进行结构化日志记录：

```python
import structlog
logger = structlog.get_logger()
logger.info("message", key="value")
```

日志级别可通过环境变量 `LOG_LEVEL` 控制。

## 性能考量

### 后端

- 使用异步 SQLAlchemy 2.0 提高并发性能
- 数据库连接池配置在 `app/core/config.py`
- Redis 用于缓存和会话管理

### 前端

- Next.js 15 App Router 支持服务端渲染
- 使用 Zustand 进行轻量级状态管理
- 骨架屏提升感知性能

## 安全注意事项

- `ADMIN_API_KEY` 启用后，所有业务接口需要认证
- API Key 通过自定义请求头传递（默认 `X-API-Key`）
- 生产环境应配置 HTTPS
- 敏感配置应通过环境变量传递，不要提交到代码仓库
