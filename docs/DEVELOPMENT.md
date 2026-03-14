# 开发手册

本手册面向继续维护 AI Novel Agent 的开发者，目标是说明开发环境、运行方式、验证路径与日常协作约定。

## 工作区环境

当前仓库使用以下本地环境：

- `backend/.venv`：后端 Python 虚拟环境
- `frontend/node_modules`：前端依赖环境
- `backend/.env`：后端本地运行配置
- `frontend/.env.local`：前端本地运行配置

仓库根目录的 `/.venv` 不参与项目运行，可以视为一次性产物。

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
./.venv/bin/ruff check app tests
./.venv/bin/python -m mypy app
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### 运行约定

- 后端命令应在 `backend/` 目录内执行，以便 `Settings` 正确解析 `.env`
- Shell 环境变量优先级高于 `.env`；如果终端或 IDE 注入了通用变量，例如 `DEBUG=release`，当前配置层会兼容常见 release/prod 拼写，但本地运行值仍应以 `backend/.env` 为准
- SQLite 仅用于测试与轻量验证；目标运行环境仍然是 PostgreSQL + pgvector
- 单用户模式是当前明确边界：`PERSONAL_USER_EMAIL` 和 `PERSONAL_USER_NAME` 决定本地归属用户

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
- 前端脚本通过 `node` 直接调用本地 CLI，不依赖 `node_modules/.bin` 的可执行位
- 全局样式入口由 `frontend/app/layout.tsx` 引入 `frontend/app/globals.css`
- 前端排版使用本地 serif 字体栈，不依赖外部字体服务
- Docker 前端运行目录是 `frontend/.next-docker`；它属于运行态目录，不应由通用清理命令在服务运行时删除

## Docker 开发

Docker Compose 提供一套完整的本地联调环境，包含前端、后端、PostgreSQL 和 Redis。

```bash
cd infra
docker compose up -d
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
```

运行说明：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`
- 数据库宿主机端口：`5433`
- 健康检查：`http://localhost:8000/api/v1/health`

健康接口会同时报告 API、数据库和 Redis 的运行状态，适合作为容器启动后的第一道检查。

## 验证路径

### 仓库级验证

```bash
make verify
```

它包含：

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

说明：

- `verify.py` 用于快速导入 / OpenAPI / 路由检查
- `verify_sqlite_integration.py` 用于无外部依赖的 HTTP 集成验证
- `verify_api_integration.py` 用于联调环境下的 live backend smoke

## 清理规则

```bash
make clean
```

`make clean` 会清理本地缓存与 `frontend/.next`，但不会删除：

- `backend/.venv`
- `frontend/node_modules`
- 本地 `.env` 文件
- `frontend/.next-docker`

最后这一点是刻意保留的，因为它是 Docker 前端 dev server 的运行目录。
