# AI Novel Agent

AI Novel Agent 是一个面向个人长期创作的 Agent 化长篇小说工作台。它把项目管理、人物设定、世界观、章节场景、记忆检索与导出整合在同一套流程里，但主入口不再是零散表单，而是项目内的 Agent Workspace。


## 核心能力

- 项目管理：建立作品、维护题材、受众、目标字数与摘要
- 角色与世界观：沉淀人物档案、设定条目与背景信息
- 章节与场景：按创作结构推进内容，而不是散落在独立文档里
- Agent Workspace：用自然语言下达创作与修改指令，先看完整计划与预览，再确认执行
- Agent Profile：项目可绑定不同写作 profile；当前内置 `default` 与 `xianxia_intrigue`
- 记忆与检索：支持 embedding 驱动的内容记忆
- 内容导出：导出 TXT 与 Markdown

## 推荐运行方式

推荐使用 Docker Compose。它会同时启动前端、后端、PostgreSQL 和 Redis，适合作为本地长期使用环境。

### 运行前准备

- Docker
- Docker Compose
- 可用的聊天模型 API Key
- 可用的 embedding API Key

## 快速开始

### 1. 配置后端环境

```bash
cd backend
cp .env.example .env
```

至少需要确认以下配置：

```env
LLM_API_KEY=你的聊天模型API_KEY
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

PERSONAL_USER_EMAIL=writer@local
PERSONAL_USER_NAME=Personal Writer
ADMIN_API_KEY=
```

配置要点：

- `LLM_*` 用于聊天与生成
- `AGENT_SKILLS_DIR` 可选；留空时使用内置 profiles，指向自定义目录后可新增或覆盖某个 profile
- `EMBEDDING_*` 留空时，会复用聊天模型的 `API_KEY` 与 `BASE_URL`
- `EMBEDDING_DIMENSION` 必须与 embedding 模型真实输出维度一致
- `PERSONAL_USER_*` 定义本地单用户身份
- `ADMIN_API_KEY` 可选；启用后，前端首页会提供本地保存入口

### 2. 启动服务

```bash
cd infra
docker compose up -d
```

如果你的环境仍使用旧命令，也可以执行：

```bash
docker-compose up -d
```

### 3. 访问服务

- 前端：`http://localhost:3000`
- 后端文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`
- PostgreSQL（宿主机访问）：`localhost:5433`

说明：

- 宿主机数据库端口固定映射到 `5433`，用于避开本机已有的 `5432`
- 健康检查会返回 API 存活状态，以及数据库和 Redis 的实时连通性

## 首次使用流程

1. 打开首页
2. 如果启用了 `ADMIN_API_KEY`，先在首页保存 Key
3. 创建一个项目
4. 进入项目后维护人物、世界观、章节和场景
5. 进入项目后的主入口是 Agent Workspace
6. 直接输入自然语言指令，例如创建人物、修改设定、重写某一章节
7. 先检查 Agent 生成的执行计划与预览，再确认执行
8. 如果计划包含高风险正文覆盖，系统会要求二次确认
9. 需要时再进入人物、世界观、章节、场景页面做手动复核或微调

## Skill 配置

Agent Workspace 默认使用后端内置的 profile-aware skills。

- 通用 profile：`backend/app/agent_skills/`
- 仙侠权谋 profile：`backend/app/agent_profiles/xianxia_intrigue/`

项目级 profile 在创建项目或编辑项目时选择。当前内置：

- `default`
- `xianxia_intrigue`

如果你需要替换其中一部分行为，而不是直接改 Python 代码，可以在 `backend/.env` 中设置：

```env
AGENT_SKILLS_DIR=/absolute/path/to/your/agent_profiles
```

覆盖目录只需要放你要新增或替换的 profile，未提供的部分会继续使用内置版本。目录结构保持 profile 根目录形式，例如：

```text
custom-agent-profiles/
└── xianxia_intrigue/
    ├── planner/
    │   └── SKILL.md
    └── operations/
        └── write-chapter-content/
            └── SKILL.md
```

运行中可以通过以下接口检查当前配置：

- `GET /api/v1/agent/profiles`
- `GET /api/v1/agent/skills`
- `GET /api/v1/agent/skills?project_id=...`

## 本地手动运行

如果你不使用 Docker，需要自行准备 PostgreSQL 与 Redis。

### 后端

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 运行检查

推荐在启动后先检查一次健康接口：

```bash
curl http://localhost:8000/api/v1/health
```

典型返回结构：

```json
{
  "status": "healthy",
  "mode": "single_user",
  "database": "healthy",
  "redis": "healthy"
}
```

其中：

- `status` 表示 API 本身可响应
- `database` 表示数据库连通性
- `redis` 表示 Redis 连通性

## 常用命令

```bash
# 启动
cd infra && docker compose up -d

# 停止
cd infra && docker compose down

# 查看日志
cd infra && docker compose logs -f backend
cd infra && docker compose logs -f frontend

# 仓库级校验
make verify
```

## 常见问题

### 1. 页面能打开，但接口返回 401 / 403

通常是已经设置了 `ADMIN_API_KEY`，但浏览器里还没有保存。回到首页保存一次即可。

### 2. Agent 生成了计划，但没有真正修改数据

这是当前设计的正常行为。项目主流程是“先计划、后执行”，所以 Agent 会先生成一组待确认操作；只有你点击确认执行后，数据才会真正写入。

### 3. 我想替换某个写作或设定 skill

优先使用 `AGENT_SKILLS_DIR` 覆盖内置 skill，而不是直接改后端代码。覆盖后可以访问 `GET /api/v1/agent/skills`，确认当前加载的是你自己的文件。

### 4. 记忆或 embedding 功能报错

优先检查：

- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`

如果数据库已经按旧维度初始化，修改模型后需要同步迁移或重建。

### 5. 前端容器运行时出现异常

Docker 前端 dev server 使用 `frontend/.next-docker` 作为运行目录。这个目录不应在服务运行时手动删除；如果误删，执行一次：

```bash
cd infra
docker compose restart frontend
```

即可恢复。

## 项目结构

```text
ai-novel-agent/
├── backend/      # FastAPI 后端
├── frontend/     # Next.js 前端
├── infra/        # Docker Compose 配置
├── docs/         # 开发与状态说明
└── Makefile      # 常用校验命令
```

## 延伸文档

- [开发手册](docs/DEVELOPMENT.md)
- [项目状态](docs/STATUS.md)
- [后端手册](backend/README.md)

## License

MIT
