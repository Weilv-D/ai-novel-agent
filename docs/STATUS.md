# AI Novel Agent - 项目进度

## 已完成 (Phase 1 进行中)

### 文档修正
- [x] 修正 MVP 工期不一致 (10 周 -> 12 周)
- [x] 统一命名规范: WorldSetting (模型) / world_settings (API/表)
- [x] 明确 MVP 边界: 包含简化版 API Key 认证和快照回滚

### Phase 1: 后端骨架 (Week 1-2)
- [x] 项目结构创建
- [x] pyproject.toml 配置
- [x] 核心配置模块 (config, logging, security)
- [x] 数据库会话工厂
- [x] 所有 SQLAlchemy 模型定义
  - User, Project, Character, WorldSetting
  - Volume, Chapter, Scene
  - Suggestion, Memory, Snapshot, Dependency
- [x] Pydantic Schemas (health, project, character, world_setting, chapter, scene, suggestion)
- [x] FastAPI main.py 入口
- [x] API 路由结构 + health check endpoint (无数据库依赖)
- [x] Alembic 迁移配置
- [x] 初始 Alembic 迁移脚本 (所有表结构)
- [x] 基础测试配置 (使用 SQLite，无外部依赖)
- [x] Health check 测试通过

### 待办 (Phase 1 剩余)
- [x] Docker Compose 本地开发配置 (已存在于 infra/docker-compose.yml)
- [ ] 环境依赖安装验证 (需 Python 3.11+ + pip/venv 或 Docker)
- [ ] 启动并验证所有服务 (需 Docker 或本地 PostgreSQL)
- [ ] LLM Service 基础封装

## 下一步 (Phase 2)
- 前端 Next.js 项目初始化
- 基础 UI 组件和布局

## 项目结构
```
ai-novel-agent/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API 路由
│   │   ├── core/            # 配置、日志、安全
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # 业务逻辑 (待实现)
│   │   ├── agents/          # Agent 编排 (待实现)
│   │   ├── db/              # 数据库会话
│   │   └── main.py          # FastAPI 入口
│   ├── tests/               # 测试
│   ├── alembic/             # 数据库迁移
│   ├── scripts/             # 工具脚本
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                # 待创建
├── infra/
│   └── docker-compose.yml   # 本地开发
└── docs/                    # PRD, TECH_ARCH, MVP_SCOPE, IMPLEMENTATION_PLAN
```

## 关键决策
- 后端: FastAPI + SQLAlchemy 2.0 (async)
- 数据库: PostgreSQL 16 + pgvector
- 向量存储: MVP 使用 pgvector (V2 迁移到 Qdrant)
- 认证: MVP 简化为 API Key (无复杂权限)
