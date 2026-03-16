# AI Novel Agent Backend

后端基于 FastAPI，负责对象数据、Agent 工作流、风险控制、执行校验、记忆检索、导出和健康检查。它服务于独立实例运行模式，不维护 `User` 实体，也不为项目绑定归属用户。

如果你要理解整个系统的实际落地方式，先读 [docs/TECH_IMPLEMENTATION.md](../docs/TECH_IMPLEMENTATION.md)。本文聚焦后端职责、目录结构、运行方式和质量门。

## 后端职责

- 提供项目、人物、世界观、卷、章、场景的 CRUD 接口
- 提供 Snapshot、Dependency、Memory、Suggestion、Export 接口
- 提供 Agent Workspace 所需的线程、消息、run、operation、checkpoint 接口
- 提供 legacy chat、流式响应、自动摘要和连续性检查接口
- 执行实例级访问控制、健康检查和数据初始化

## 运行模型

后端当前采用以下运行模型：

- 实例模式：`standalone`
- 访问控制：实例级 `ADMIN_API_KEY`
- 数据边界：所有项目和运行数据直接归属于当前实例
- 主流程：preview-first、confirm-then-execute
- 风险控制：高风险正文覆盖需要二次确认
- 执行保障：落库后经过 verification gate 才能完成 run

## 目录结构

```text
backend/
├── app/
│   ├── api/v1/            # HTTP 路由
│   ├── core/              # 配置、安全、日志
│   ├── db/                # 会话、初始化
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic schema
│   ├── services/          # 业务与 Agent 服务
│   ├── agents/            # legacy agent orchestration
│   ├── agent_skills/      # 通用 planner / operation skills
│   └── agent_profiles/    # 项目级 profile 覆盖
├── alembic/               # 数据库迁移
├── scripts/               # 验证与开发脚本
├── tests/                 # pytest 测试
├── pyproject.toml
└── verify.py
```

## 核心实现层次

### API 层

`app/api/v1/` 提供所有 HTTP 接口。路由层负责：

- 参数校验
- 会话依赖注入
- 实例级访问控制
- 把请求转交给 service 层

### Service 层

`app/services/` 是后端的核心实现层。它包括：

- CRUD service
- `agent_workflow.py`：Agent 主工作流
- `agent_skill.py`：profile / skill 加载
- `agent_risk.py`：风险分类与 policy registry
- `agent_contract.py`：execution contract 装配
- `snapshot.py`、`memory.py`、`dependency.py` 等领域服务

### Model / Schema 层

- `app/models/` 定义持久化结构
- `app/schemas/` 定义稳定 API contract

对 Agent 来说，当前显式暴露的核心 contract 包括：

- `execution_contract`
- `risk_summary`
- `verification_status / verification_summary`
- `compact_policy / planner_window / retained_window / active_bundle_contract`

## Agent 工作流

当前主流程稳定在项目级 `thread / run / operation`。

### 线程与消息

- 每个项目有一个默认 `AgentThread`
- 用户发送消息后，先写入 `AgentMessage`
- 系统返回一个待确认 `AgentRun`

### 计划与执行

- planner 先生成用户可见 operations 和内部 subtasks
- 普通写入经过一次确认
- 高风险正文覆盖经过二次确认
- 执行阶段复用现有 CRUD service，不通过 HTTP 回调自己

### 内部执行层

当前 workflow 内部显式建模了这些 child unit：

- `planner`
- `researcher`
- `writer`
- `editor`
- `continuity`
- `executor`

它们已经具备显式 child unit contract、执行 trace 和恢复边界，但还不是独立运行的 child session。

### Verification Gate

run 只有在以下校验通过后才会进入 `completed`：

- 字段级校验
- snapshot linkage 校验
- snapshot-derived semantic 校验
- content transition 校验
- domain-level semantic 校验

### Compact Flow

长线程通过 checkpoint 压缩上下文。当前 planner 输入以两种模式运行：

- `recent_window`
- `checkpoint_delta`

压缩相关 contract 通过 run 和 checkpoint 响应显式返回，不需要前端解析非结构化 `meta`。

## Profile 与 Skill

项目可以绑定 `agent_profile_id`。当前内置：

- `default`
- `xianxia_intrigue`

运行时支持：

- `GET /api/v1/agent/profiles`
- `GET /api/v1/agent/skills`
- `GET /api/v1/agent/skills?project_id=...`
- `GET /api/v1/agent/risk-policies`
- `GET /api/v1/agent/capabilities`

`AGENT_SKILLS_DIR` 用于按 profile 根目录新增或覆盖 skill。

## 运行环境

- Python `>= 3.11`
- PostgreSQL 16 + pgvector
- Redis

SQLite 只用于测试和轻量验证，不作为长期运行环境。

## 初始化

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
```

后端命令应在 `backend/` 目录内执行，这样配置系统才能正确解析本地 `.env`。

## 常用命令

```bash
# 快速验证
./.venv/bin/python verify.py

# 测试
./.venv/bin/python -m pytest

# 静态检查
./.venv/bin/ruff check app tests scripts
./.venv/bin/python -m mypy app

# 开发服务
./.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

从仓库根目录执行完整验证：

```bash
make verify
```

## 验证脚本

- `verify.py`：导入、OpenAPI、路由与 Alembic 快速检查
- `scripts/verify_sqlite_integration.py`：SQLite 驱动的 HTTP 集成验证
- `scripts/verify_api_integration.py`：联调环境下的 live API smoke
- `scripts/start_dev.sh`：迁移后启动开发服务

## 健康检查

`/api/v1/health` 返回：

- API 存活状态
- 实例模式与访问控制信息
- 数据库与 Redis 的实时连通性

健康接口不会把依赖异常误报成 API 不可访问，但会明确区分各依赖状态。

## 质量门

当前后端质量门：

- `ruff check app tests scripts`
- `mypy app`
- `pytest`

在当前仓库状态下，这组命令应保持通过。

## 接口文档

- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`
- Health：`http://localhost:8000/api/v1/health`
