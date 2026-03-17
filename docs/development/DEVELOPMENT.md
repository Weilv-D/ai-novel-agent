# 开发与部署指南

最后更新：2026-03-17

## 1. 环境要求

### 后端

- Python `>= 3.11`
- PostgreSQL `>= 16`（生产建议，需 pgvector）
- Redis `>= 7`

### 前端

- Node.js `>= 18`
- npm `>= 9`

### E2E

- Playwright 浏览器依赖
- 本仓库根目录 `npm install`

## 2. 安装

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

### E2E

```bash
npm install
npx playwright install --with-deps chromium
```

## 3. 关键配置

后端配置文件：`backend/.env`

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | 数据库连接串 |
| `REDIS_URL` | Redis 连接串 |
| `ADMIN_API_KEY` | 实例级访问 key |
| `API_KEY_HEADER` | 默认 `X-API-Key` |
| `LLM_API_KEY` | 聊天模型 API key |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 默认聊天模型 |
| `EMBEDDING_API_KEY` | 向量模型 API key，可复用 LLM key |
| `EMBEDDING_BASE_URL` | 向量接口地址 |
| `EMBEDDING_MODEL` | 默认 embedding 模型 |
| `EMBEDDING_DIMENSION` | embedding 维度 |
| `AGENT_SKILLS_DIR` | 自定义 profile/skill 根目录 |
| `AGENT_E2E_MODE` | E2E fixture 模式开关 |
| `AGENT_E2E_FIXTURE_PATH` | E2E fixture 目录 |

## 4. 本地运行

### 推荐：Docker Compose

```bash
cd infra
docker compose up -d
```

默认入口：

- 前端：`http://localhost:3000`
- 后端 OpenAPI：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`

### 分开运行

后端：

```bash
cd backend
./.venv/bin/python -m uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm run dev
```

## 5. 质量门

### 后端

```bash
cd backend
./.venv/bin/python -m ruff check app tests scripts
./.venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

### 前端

```bash
cd frontend
npm run lint
npm run type-check
npm run build
```

说明：

- `npm run type-check` 已改为 `next typegen + tsc --noEmit`，不再依赖上一次 build 残留的 `.next/types`

### E2E

```bash
npm run e2e
```

说明：

- Playwright 后端启动脚本会先清理 `backend/e2e_test.db`，避免旧 SQLite schema 污染当前用例

## 6. 常用验证

### 导出验证

```bash
curl -H "X-API-Key: <key>" \
  "http://localhost:8000/api/v1/projects/<project_id>/export?format=docx" \
  -o novel.docx
```

### 时间线验证

```bash
curl -H "X-API-Key: <key>" \
  "http://localhost:8000/api/v1/projects/<project_id>/timeline"
```

### Redis 缓存验证

```bash
redis-cli KEYS '*'
```

## 7. 故障排查

- `sqlite3.OperationalError ... no column named ...`：
  - 多见于 E2E 脏数据库；重新跑 `npm run e2e` 即会自动清理
- `TS6053 ... .next/types/... not found`：
  - 直接执行 `npm run type-check`；当前脚本会自动 `typegen`
- Redis 不可用：
  - 系统会降级为无缓存运行，但缓存命中验证会失败
