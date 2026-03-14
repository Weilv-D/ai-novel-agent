# AI Novel Agent

AI 驱动的长篇小说写作工具，当前仓库已经包含完整的 FastAPI 后端、Next.js 前端、Agent 编排层、记忆/快照/依赖分析能力，以及可运行的测试体系。

## 当前状态

- 后端测试集：`395` collected, `393 passed`, `2 skipped`
- 前端：`npm run build` 和 `npm run lint` 可通过
- 仓库级完整校验入口：`make verify`
- 本地有效环境：
  - `backend/.venv`
  - `frontend/node_modules`
  - `backend/.env`
  - `frontend/.env.local`
- 仓库根目录 `/.venv` 不参与项目运行，属于可清理遗留物
- 当前后端工作流已按“个人单用户使用”实现

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic |
| 数据库 | PostgreSQL 16 + pgvector |
| 测试 | pytest + pytest-asyncio + httpx |
| 前端 | Next.js 15 + TypeScript + Tailwind CSS + Zustand |
| LLM 接入 | OpenAI SDK 兼容接口 |
| 部署 | Docker Compose |

## 快速开始

### 本地开发

```bash
# backend
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
./.venv/bin/python -m pytest
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# frontend
cd ../frontend
npm install
npm run lint
npm run dev
```

### Docker 启动

```bash
cd infra
docker compose up -d
```

如果你的机器只有旧版命令，也可以使用 `docker-compose up -d`。

## 环境变量

`backend/.env` 里最关键的是 LLM 与 embedding 配置。两者都走 OpenAI 兼容接口。

```env
LLM_API_KEY=...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_DIMENSION=4096

PERSONAL_USER_EMAIL=writer@local
PERSONAL_USER_NAME=Personal Writer
ADMIN_API_KEY=
```

说明：

- 如果聊天模型和 embedding 走同一提供商，可只配置 `LLM_*`，把 `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` 留空。
- `EMBEDDING_DIMENSION` 必须和模型真实输出维度一致；变更后需要同步数据库结构。
- 运行后端命令时要先进入 `backend/`，因为配置默认从当前工作目录的 `.env` 读取。
- `PERSONAL_USER_*` 控制本地单用户身份；项目数据默认归属于这个账号。
- `ADMIN_API_KEY` 留空时前端/脚本可直接访问；填入后，除 `/` 和 `/api/v1/health` 外的接口都需要携带同一值。前端会通过健康接口自动识别 `API_KEY_HEADER`，首页也提供浏览器本地保存入口。

## 常用命令

仓库根目录提供了统一入口：

```bash
make backend-test
make backend-lint
make backend-typecheck
make backend-verify
make frontend-build
make frontend-lint
make verify
make clean
```

`make verify` 会串起后端 lint/typecheck/test 和前端 lint/build。`make clean` 只清理缓存、前端构建产物和仓库根目录遗留 `/.venv`，不会删除 `backend/.venv`、`frontend/node_modules` 或本地 `.env` 文件。

## 项目结构

```text
ai-novel-agent/
├── backend/
│   ├── app/
│   │   ├── agents/        # Agent 编排与专用 agent
│   │   ├── api/v1/        # FastAPI 路由
│   │   ├── core/          # 配置、异常、日志、安全
│   │   ├── db/            # 数据库引擎与初始化
│   │   ├── models/        # SQLAlchemy 模型
│   │   ├── schemas/       # Pydantic 请求/响应模型
│   │   └── services/      # 业务逻辑层
│   ├── alembic/           # 迁移配置
│   ├── scripts/           # 手工验证与数据脚本
│   └── tests/             # pytest 套件
├── frontend/
│   ├── app/               # Next.js App Router 页面
│   ├── components/        # UI 与业务组件
│   ├── lib/               # API client、stores、类型
│   └── scripts/           # 前端手工联调脚本
├── docs/                  # 状态、开发说明、架构与需求文档
├── infra/                 # Docker Compose 与启动脚本
└── Makefile               # 常用开发命令
```

## 主要能力

- 项目、人物、世界观、卷/章/场景 CRUD
- Suggestions 三态流转：`draft -> patched -> committed`
- Dependencies 影响分析
- Snapshots 版本回滚准备
- Memories 向量检索与自动摘要
- Agent chat / stream / continuity check / auto summarize
- TXT / Markdown 导出

## 文档

- [开发说明](docs/DEVELOPMENT.md)
- [项目状态](docs/STATUS.md)
- [产品需求文档](docs/PRD.md)
- [技术架构设计](docs/TECH_ARCH.md)
- [实施计划](docs/IMPLEMENTATION_PLAN.md)

## License

MIT
