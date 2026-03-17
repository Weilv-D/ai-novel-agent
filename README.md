# AI Novel Agent

AI Novel Agent 是一个面向个人长期创作的 Agent 化小说工作台。它把项目、人物、世界观、章节、场景、记忆检索与导出放进同一套工作流里，并以项目内的 Agent Workspace 作为主入口。

这个仓库当前服务于独立实例使用场景。系统不实现用户注册、登录和项目归属用户模型；访问控制保留为实例级 API key。

## 产品形态

AI Novel Agent 由三部分组成：

- 前端工作台：Next.js App Router，负责项目界面、Agent Workspace 和对象编辑页
- 后端服务：FastAPI，负责数据持久化、Agent 工作流、风险控制、校验与导出
- 基础设施：PostgreSQL、pgvector、Redis，以及本地 Docker Compose 运行环境

## 核心能力

- 项目管理：维护作品名称、题材、摘要、项目大纲、目标字数与 profile
- 人物与世界观：管理角色档案、关系、设定与背景条目
- 双层规划体系：以 `项目大纲 -> 卷细纲 -> 章纲 -> 场景/正文` 组织长篇创作
- 章节与场景：按卷、章、场景组织创作内容
- Agent Workspace：用自然语言提出创作、修改、续写和重构指令
- Preview-first 流程：Agent 先生成计划和预览，再确认执行
- 风险控制：按风险策略动态门禁，长文本覆盖或多对象重写会触发二次确认
- Verification Gate：落库结果经过字段、快照、内容迁移和业务语义校验
- Domain Verification：人物名称唯一性、年龄合法性；设定内容完整性、分类唯一性
- 长线程压缩：使用 checkpoint、planner window、retained window 和 active bundle contract 管理长期上下文
- Profile / Skill 体系：项目可绑定不同写作 profile，并用文件化 skill 规范 planner 和 operation
- 记忆检索与导出：支持 embedding、相似检索、TXT / Markdown 导出
- 项目包导出导入：完整项目数据打包、迁移与恢复

## 数据层级

当前项目结构正式收敛为：

`Project.story_outline（项目大纲） -> Volume.outline（卷细纲） -> Chapter.outline（章纲） -> Scene（写作执行层）`

约定如下：

- `summary` 是项目简介，不承担完整结构规划
- `story_outline` 是项目级总纲，描述长期目标、主线因果链和阶段推进
- `Volume` 是正式卷层，`outline` 承载卷级目标、支线网络和卷末收束
- `Chapter.title + Chapter.outline` 共同构成卷下章纲
- `Scene` 继续承担正文组织与写作执行，不额外引入 beat 实体

兼容迁移行为：

- 旧项目升级后会自动补一个默认卷（默认标题为“第一卷”）
- 原先未挂卷的章节会迁入默认卷
- 旧 `summary / notes` 会参与 `story_outline` 初始回填

## 运行方式

推荐使用 Docker Compose。它会同时启动：

- 前端 `frontend`
- 后端 `backend`
- PostgreSQL
- Redis

### 前置条件

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

至少确认以下配置：

```env
LLM_API_KEY=你的聊天模型API_KEY
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

ADMIN_API_KEY=
```

配置说明：

- `LLM_*` 用于对话、规划和正文生成
- `EMBEDDING_*` 留空时，会复用聊天模型的 `API_KEY` 与 `BASE_URL`
- `EMBEDDING_DIMENSION` 必须和 embedding 模型真实输出维度一致
- `ADMIN_API_KEY` 可选；配置后，业务接口要求客户端在指定请求头中携带它
- `AGENT_SKILLS_DIR` 可选；用于新增或覆盖 profile 根目录

### 2. 启动服务

```bash
cd infra
docker compose up -d
```

### 3. 打开工作台

- 前端：`http://localhost:3000`
- 后端文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`
- PostgreSQL 宿主机端口：`5433`

## 使用流程

1. 打开首页。
2. 如果启用了 `ADMIN_API_KEY`，先在首页保存访问 key。
3. 创建项目，并为项目选择合适的 Agent profile。
4. 先补项目大纲，再建立卷细纲与章纲。
5. 进入项目详情页，使用 Agent Workspace 提出自然语言指令。
6. 检查 run 生成的 operation 计划、diff 预览、风险摘要和内部执行摘要。
7. 完成一次确认；若命中高风险策略，再完成二次确认。
8. 在人物、设定、卷、章节、场景页面做复核或局部手工调整。

Agent Workspace 适合处理这些任务：

- 补写项目大纲
- 创建或修改卷细纲
- 按卷拆分章节并补章纲
- 创建新人物
- 修改角色关系或设定条目
- 创建章节、场景与结构信息
- 续写或重写章节正文
- 根据现有上下文进行一致性修订

## Profile 与 Skill

项目级 profile 决定 planner 和 operation skill 的组合。当前内置：

- `default`
- `xianxia_intrigue`

默认 skill 位置：

- 通用 skill：`backend/app/agent_skills/`
- profile 覆盖：`backend/app/agent_profiles/`

如果需要自定义 profile，可在 `backend/.env` 中设置：

```env
AGENT_SKILLS_DIR=/absolute/path/to/custom-agent-profiles
```

覆盖目录按 profile 根目录组织，例如：

```text
custom-agent-profiles/
└── xianxia_intrigue/
    ├── planner/
    │   └── SKILL.md
    └── operations/
        └── write-chapter-content/
            └── SKILL.md
```

运行时可通过以下接口查看实际加载结果：

- `GET /api/v1/agent/profiles`
- `GET /api/v1/agent/skills`
- `GET /api/v1/agent/skills?project_id=...`
- `GET /api/v1/agent/risk-policies`

## 运行检查

启动后建议先检查一次健康接口：

```bash
curl http://localhost:8000/api/v1/health
```

典型返回：

```json
{
  "status": "healthy",
  "mode": "standalone",
  "database": "healthy",
  "redis": "healthy"
}
```

说明：

- `status` 表示 API 本身可响应
- `database` 表示数据库连通性
- `redis` 表示 Redis 连通性
- `mode=standalone` 表示当前实例按独立工作台方式运行

## 本地手动运行

如果不使用 Docker，需要自行准备 PostgreSQL 与 Redis。

### 后端

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

说明：

- `alembic upgrade head` 会创建 `projects.story_outline`
- 历史项目会自动补默认卷，并把旧章节迁入卷层

### 前端

```bash
cd frontend
npm install
npm run dev
```

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

### 接口返回 401 / 403

通常是实例启用了 `ADMIN_API_KEY`，但浏览器还没有保存 key。回到首页保存一次即可。

### Agent 已生成计划，但数据没有变化

这是设计使然。系统遵循 preview-first、confirm-then-execute 流程；只有确认执行后，数据才会真正落库。

### 想替换某个写作 skill

优先使用 `AGENT_SKILLS_DIR` 覆盖 profile 根目录，再通过 `GET /api/v1/agent/skills` 验证加载结果。

### embedding 报维度错误

优先检查：

- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`

如果数据库已经按旧维度初始化，修改模型后需要同步迁移或重建。

### 前端容器运行时报错

Docker 前端 dev server 使用 `frontend/.next-docker` 作为运行目录。这个目录不应在服务运行时手动删除；如果误删，执行：

```bash
cd infra
docker compose restart frontend
```

## 仓库结构

```text
ai-novel-agent/
├── backend/      # FastAPI 后端
├── frontend/     # Next.js 前端
├── infra/        # Docker Compose 配置
├── docs/         # 使用、开发、实现与架构文档
└── Makefile      # 常用验证命令
```

## 文档索引

- [文档总览](docs/README.md)
- [后端手册](backend/README.md)
- [技术实现说明](docs/architecture/TECH_IMPLEMENTATION.md)
- [开发手册](docs/development/DEVELOPMENT.md)
- [用户手册](docs/user/USER_GUIDE.md)
- [API Reference](docs/api/API_REFERENCE.md)
- [目标架构](docs/architecture/TECH_ARCH.md)
- [项目状态](docs/qa/STATUS.md)
- [逻辑审查报告](docs/qa/REVIEW_REPORT.md)
- [测试报告](docs/qa/TEST_REPORT.md)
- [问题清单](docs/qa/ISSUE_TRACKER.md)
- [演进计划](docs/roadmap/IMPLEMENTATION_PLAN.md)

## License

MIT
