# AI Novel Agent

AI Novel Agent 是一个面向个人长期创作的 AI 长篇小说工作台。它把项目管理、人物设定、世界观、章节场景、AI 建议、记忆检索与导出整合在同一套流程里，重点不是“多功能堆叠”，而是让写作上下文始终连贯。

当前项目按单用户模式设计。所有数据归属于同一个本地个人账号，不引入注册、组织或多租户权限系统。

## 核心能力

- 项目管理：建立作品、维护题材、受众、目标字数与摘要
- 角色与世界观：沉淀人物档案、设定条目与背景信息
- 章节与场景：按创作结构推进内容，而不是散落在独立文档里
- AI 建议：保留生成、确认、应用的完整链路
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
5. 在需要时使用 AI 建议、对话、记忆和导出

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

### 2. 记忆或 embedding 功能报错

优先检查：

- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`

如果数据库已经按旧维度初始化，修改模型后需要同步迁移或重建。

### 3. 前端容器运行时出现异常

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
