# AI Novel Agent Backend

后端基于 FastAPI，负责项目数据管理、对象间关系、AI 协作接口、记忆检索、导出以及运行时健康检查。当前后端明确服务于单用户个人使用场景：系统启动后会保证本地个人用户存在，所有业务数据都归属于该用户。

## 后端职责

- 项目、人物、世界观、卷、章、场景的 CRUD
- Suggestion、Dependency、Snapshot、Memory 的持久化与查询
- Agent Workspace 所需的线程、消息、运行计划与执行接口
- legacy Agent chat、流式响应、连续性检查与摘要接口
- TXT / Markdown 导出
- 运行时健康检查与单用户访问控制

## 运行环境

- Python `>= 3.11`
- PostgreSQL 16 + pgvector
- Redis

测试与轻量验证可以使用 SQLite，但它不是目标生产/长期运行环境。

## 初始化

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
```

运行命令请保持在 `backend/` 目录内，这样配置系统才能正确解析本地 `.env`。

## 常用命令

```bash
# 快速验证
./.venv/bin/python verify.py

# 测试
./.venv/bin/python -m pytest

# 静态检查
./.venv/bin/ruff check app tests
./.venv/bin/python -m mypy app

# 开发服务
./.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

如果需要从仓库根目录执行完整验证：

```bash
cd ..
make verify
```

## 运行特性

### 单用户模式

- `PERSONAL_USER_EMAIL` / `PERSONAL_USER_NAME` 定义本地用户身份
- 启动时会自动初始化该用户记录
- `ADMIN_API_KEY` 可选；启用后，业务接口要求客户端在指定请求头中携带它

### Agent 工作流

- 每个项目有一个默认 `AgentThread`
- 用户消息会生成一个 `AgentRun`
- `AgentRun` 会先给出待确认的多步操作预览，再进入执行
- 项目可绑定 `agent_profile_id`；当前内置 `default` 与 `xianxia_intrigue`
- run 会带出内部 `subtask` 摘要，展示 planner / researcher / writer / editor / continuity
- 高风险正文覆盖会进入二次确认，而不是直接执行
- 执行阶段复用现有 CRUD service，并在落库前为目标对象创建 snapshot
- planner 与每个 operation 都由文件化 skill 驱动；通用技能位于 `app/agent_skills/`，profile 覆盖位于 `app/agent_profiles/`
- `AGENT_SKILLS_DIR` 作为 profile 根目录覆盖入口，可新增或替换某个 profile
- `GET /api/v1/agent/profiles` 与 `GET /api/v1/agent/skills?project_id=...` 可用于检查当前实际加载结果
- legacy `/api/v1/agent/chat*` 仍保留，用于次级页面和兼容路径

### 健康检查

`/api/v1/health` 返回三类信息：

- API 本身是否可响应
- 当前单用户模式与鉴权配置
- 数据库与 Redis 的实时连通性

健康接口不会因为依赖异常而把整个 API 标记为不可访问，但会明确区分 `database` / `redis` 的当前状态。

## 验证脚本

- `verify.py`：导入、OpenAPI、路由与 Alembic 快速检查
- `scripts/verify_sqlite_integration.py`：SQLite 驱动的 HTTP 集成验证
- `scripts/verify_api_integration.py`：联调环境下的 live API smoke
- `scripts/start_dev.sh`：先执行迁移，再启动开发服务

## 质量门

当前后端质量门由以下命令组成：

- `ruff check app tests`
- `mypy app`
- `pytest`

在当前仓库状态下，这组命令应当保持可通过。

## 目录结构

```text
backend/
├── app/
│   ├── agents/
│   ├── api/v1/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── services/
├── alembic/
├── scripts/
├── tests/
├── pyproject.toml
└── verify.py
```

## 接口文档

服务启动后：

- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`
- Health：`http://localhost:8000/api/v1/health`
