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

### 初始化

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
```

### 常用命令

```bash
./.venv/bin/python verify.py
./.venv/bin/python -m pytest
./.venv/bin/ruff check app tests scripts
./.venv/bin/python -m mypy app
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### 运行约定

- 后端命令应在 `backend/` 目录执行，以便 `Settings` 正确解析 `.env`
- shell 环境变量优先级高于 `.env`
- SQLite 仅用于测试和轻量验证；目标运行环境仍是 PostgreSQL + pgvector
- `AGENT_SKILLS_DIR` 是 profile 根目录覆盖入口
- `GET /api/v1/agent/profiles`、`/skills`、`/risk-policies`、`/capabilities` 是运行期排障的第一批接口

## 前端开发

### 初始化

```bash
cd frontend
npm install
```

### 常用命令

```bash
npm run dev
npm run lint
npm run build
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

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`
- 数据库宿主机端口：`5433`
- 健康检查：`http://localhost:8000/api/v1/health`

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

- [README.md](/home/weilv/workspace/prjforfun/ai-novel-agent/README.md)：使用者手册
- [backend/README.md](/home/weilv/workspace/prjforfun/ai-novel-agent/backend/README.md)：后端运行与结构说明
- [TECH_IMPLEMENTATION.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/TECH_IMPLEMENTATION.md)：当前实现
- [TECH_ARCH.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/TECH_ARCH.md)：目标架构
- [STATUS.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/STATUS.md)：交付状态与边界
- [IMPLEMENTATION_PLAN.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/IMPLEMENTATION_PLAN.md)：演进计划
