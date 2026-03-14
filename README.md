# AI Novel Agent

面向个人使用的 AI 长篇小说写作工具。它把项目管理、人物设定、世界观、章节场景、AI 建议、记忆检索和导出放在一个应用里，适合你自己长期写作时使用。

当前项目默认就是单用户模式：所有数据都归属于一个本地个人账号，不需要搭建多用户系统。

## 你可以用它做什么

- 创建小说项目
- 管理人物、世界观、卷、章、场景
- 让 AI 辅助续写、补全设定、做一致性检查
- 保存建议并逐步确认修改
- 做记忆检索和摘要
- 导出 TXT / Markdown

## 推荐启动方式

优先推荐 `Docker Compose`，最省事。

你需要先准备：

- Docker
- Docker Compose
- 一个可用的聊天模型 API Key
- 一个可用的 embedding API Key（如果和聊天模型同服务商，也可以复用）

## 第一步：配置 `backend/.env`

先复制配置文件：

```bash
cd backend
cp .env.example .env
```

至少把下面这些值改成你自己的：

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

说明：

- `LLM_*` 是聊天模型配置。
- `EMBEDDING_*` 留空时，会复用聊天模型的 `API_KEY` 和 `BASE_URL`。
- `EMBEDDING_DIMENSION` 必须和 embedding 模型真实维度一致。
- `PERSONAL_USER_*` 是你本地这个单用户应用的身份信息。
- `ADMIN_API_KEY` 可留空。留空时前端可直接访问；如果填了，前端首页会提示你保存这个 Key。

## 第二步：启动项目

### 方式 A：Docker

这是最推荐的方式。

```bash
cd infra
docker compose up -d
```

如果你的机器使用旧命令：

```bash
docker-compose up -d
```

启动后访问：

- 前端：http://localhost:3000
- 后端文档：http://localhost:8000/docs

### 方式 B：本地手动启动

如果你不想用 Docker，需要自己准备 PostgreSQL 和 Redis。

后端：

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

启动后访问：

- 前端：http://localhost:3000

## 第三步：开始使用

1. 打开首页。
2. 如果你配置了 `ADMIN_API_KEY`，先在首页保存它。
3. 创建一个项目。
4. 进入项目后开始维护人物、世界观、章节和场景。
5. 在需要的时候使用 AI 对话、建议、记忆和导出功能。

## 重要配置说明

### 关于 embedding 维度

如果你改了 embedding 模型，必须同步确认：

- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`

这两个值不一致时，记忆功能会报错。

### 关于单用户模式

这个项目现在明确面向个人使用，不做多用户权限隔离。也就是说：

- 所有项目都属于同一个本地用户
- 不需要注册登录
- 如果你想加一个简单入口保护，就设置 `ADMIN_API_KEY`

### 关于 API Key 请求头

如果你设置了 `ADMIN_API_KEY`，前端会自动从后端健康接口读取当前使用的请求头名称，不需要你手工改前端代码。

## 常见问题

### 1. 前端打不开或接口报 401 / 403

通常是你设置了 `ADMIN_API_KEY`，但浏览器里还没保存。回到首页保存一次即可。

### 2. 记忆 / embedding 相关功能报错

先检查：

- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`

如果你已经用旧维度初始化过数据库，改模型后还需要重建数据库或做迁移。

### 3. 后端启动失败

本地启动时先确认：

```bash
cd backend
./.venv/bin/alembic upgrade head
```

另外还要确认 PostgreSQL 和 Redis 已经可用。

## 项目结构

```text
ai-novel-agent/
├── backend/      # FastAPI 后端
├── frontend/     # Next.js 前端
├── infra/        # Docker Compose
├── docs/         # 开发和架构文档
└── Makefile      # 常用命令
```

## 开发相关

如果你要继续开发、调试或做代码验证，直接看下面这些文档：

- [开发说明](docs/DEVELOPMENT.md)
- [项目状态](docs/STATUS.md)
- [后端说明](backend/README.md)

仓库级完整校验命令：

```bash
make verify
```

## License

MIT
