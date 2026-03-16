# 开发与部署指南

最后更新：2026-03-16

## 1. 环境要求

### 后端

- Python >= 3.11
- PostgreSQL >= 16（生产建议，需 pgvector）
- Redis >= 7

### 前端

- Node.js >= 18
- npm >= 9

### 可选（端到端测试）

- Playwright 浏览器依赖（`npx playwright install --with-deps chromium`）

## 2. 依赖安装

### 后端

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
```

### 前端

```bash
cd frontend
npm install
```

### E2E（仓库根目录）

```bash
npm install
npx playwright install --with-deps chromium
```

## 3. 配置说明

后端配置文件：`backend/.env`

关键参数：

| 变量 | 是否必填 | 说明 |
|---|---|---|
| `DATABASE_URL` | 是 | 数据库连接串（生产建议 PostgreSQL） |
| `REDIS_URL` | 建议 | Redis 连接串 |
| `LLM_API_KEY` | 建议 | Agent 规划与生成所需 |
| `LLM_BASE_URL` | 否 | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 否 | 聊天模型 |
| `EMBEDDING_API_KEY` | 可选 | 留空时复用 LLM key |
| `EMBEDDING_BASE_URL` | 可选 | 留空时复用 LLM base url |
| `EMBEDDING_MODEL` | 否 | embedding 模型 |
| `EMBEDDING_DIMENSION` | 是 | 必须与 embedding 实际维度一致 |
| `ADMIN_API_KEY` | 可选 | 配置后业务接口要求鉴权 |
| `API_KEY_HEADER` | 否 | 默认 `X-API-Key` |
| `AGENT_SKILLS_DIR` | 可选 | 自定义 profile/skill 根目录 |
| `AGENT_E2E_MODE` | 可选 | E2E fixture 模式开关 |
| `AGENT_E2E_FIXTURE_PATH` | 可选 | fixture 路径 |

前端配置文件：`frontend/.env.local`

| 变量 | 默认值 | 说明 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | 后端地址 |

## 4. 本地启动步骤

### 4.1 后端（本地）

```bash
cd backend
./.venv/bin/alembic upgrade head
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

迁移说明：

- 最新迁移会新增 `projects.story_outline`
- 旧项目如无卷层，会自动补默认卷“第一卷”
- 旧章节会迁入默认卷，后续前端按卷展示章纲

### 4.2 前端（本地）

```bash
cd frontend
npm run dev
```

访问：

- 前端：`http://localhost:3000`
- Swagger：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`

## 5. Docker 部署（推荐联调）

```bash
cd infra
docker compose up -d
docker compose logs -f backend
docker compose logs -f frontend
```

默认端口：

- 前端：`3000`
- 后端：`8000`
- PostgreSQL：`5433`
- Redis：`6379`

停止：

```bash
cd infra
docker compose down
```

## 6. 验证方法

### 6.1 后端质量门

```bash
cd backend
./.venv/bin/ruff check app tests
./.venv/bin/python -m mypy app
./.venv/bin/python -m pytest tests
```

### 6.2 前端质量门

```bash
cd frontend
npm run lint
npm run build
```

### 6.3 E2E

```bash
cd /path/to/ai-novel-agent
npm run e2e
```

### 6.4 一键验证（仓库根目录）

```bash
make verify
```

## 7. 使用示例（开发调试）

### 7.1 创建项目

```bash
curl -X POST 'http://localhost:8000/api/v1/projects' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -d '{
    "name": "示例项目",
    "genre": "xianxia",
    "target_audience": "adult",
    "story_outline": "项目大纲：主角从入局、立势到改写格局，按三卷推进。",
    "agent_profile_id": "default"
  }'
```

预期结果：返回 `201` 与 `ProjectResponse`。

### 7.2 创建卷细纲

```bash
curl -X POST 'http://localhost:8000/api/v1/volumes' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -d '{
    "project_id": "<project_id>",
    "volume_number": 1,
    "title": "第一卷 北地试锋",
    "outline": "卷细纲：完成入局、资源争夺、支线铺设与卷末翻盘。"
  }'
```

预期结果：返回 `201` 与 `VolumeResponse`。

### 7.3 Agent 生成待确认计划

```bash
curl -X POST 'http://localhost:8000/api/v1/agent/threads' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -d '{"project_id":"<project_id>"}'
```

```bash
curl -X POST 'http://localhost:8000/api/v1/agent/threads/<thread_id>/messages' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -d '{"content":"先补项目大纲，再创建第一卷细纲并拆成三个章纲","context":{},"stream":false}'
```

预期结果：返回 `run.status=awaiting_confirmation`（或按风险策略返回高风险待确认态）。

### 7.4 导出项目包

```bash
curl -X GET 'http://localhost:8000/api/v1/projects/<project_id>/package' \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  -o project_package.zip
```

预期结果：下载 zip，包含 `manifest.json` 和 `project_bundle.json`。

## 8. 注意事项

### 8.1 性能

- 长线程项目建议关注 `AgentThreadCheckpoint` 规模与 compact 触发频率。
- 大型项目导入导出会放大 I/O 与序列化耗时，建议在低峰执行。
- 章节在前端创建时要求选择卷；API 若未提供 `volume_id`，会自动落到项目默认卷。

### 8.2 安全

- 生产环境必须设置强随机 `ADMIN_API_KEY` 与 `SECRET_KEY`。
- 建议在网关层补充限流、IP 白名单与审计日志。

### 8.3 兼容性

- SQLite 主要用于测试和 E2E，不建议作为生产主库。
- 变更 embedding 模型时必须同步 `EMBEDDING_DIMENSION`，否则检索与导入会出现降级行为。
- 项目包 `1.1.0` 起正式包含 `story_outline` 与卷层级数据。
