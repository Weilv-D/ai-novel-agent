# AI 超长篇小说写作 Agent - 技术架构设计

## 文档信息
- 项目名称：AI 超长篇小说写作 Agent 应用
- 文档类型：技术架构文档（TECH_ARCH）
- 版本：v1.0
- 状态：初版
- 创建日期：2026-03-11

---

## 1. 整体架构

采用经典的 **前后端分离 + 微服务演进** 架构：

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────────┐  │
│  │ Editor    │ │ Knowledge │ │ Outline   │ │ Project Dashboard│  │
│  │ (TipTap)  │ │ Graph     │ │ Tree View │ │                 │  │
│  └───────────┘ └───────────┘ └───────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP/WS
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Auth │  Rate Limit │  CORS │  Request Validation       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Services (FastAPI)                    │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────────┐  │
│  │ Project   │ │ Knowledge │ │ Editor    │ │ Agent           │  │
│  │ Service   │ │ Service   │ │ Service   │ │ Orchestrator    │  │
│  └───────────┘ └───────────┘ └───────────┘ └─────────────────┘  │
│  ┌───────────┐ ┌───────────┐ ┌─────────────────────────────────┐ │
│  │ Suggestion│ │ Patch/    │ │ Continuity &                    │ │
│  │ Service   │ │ Commit    │ │ Impact Analysis                 │ │
│  └───────────┘ └───────────┘ └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          ↓              ↓              ↓                ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ PostgreSQL  │ │  Qdrant     │ │   Redis     │ │  LLM API    │
│ (主数据)    │ │ (向量存储)  │ │ (缓存/队列) │ │  (模型网关)  │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 2. 技术栈确定

| 层级 | 技术选择 | 理由 |
|------|---------|------|
| 前端 | Next.js 14 (App Router) | React 生态，SSR 支持，便于 SEO |
| 编辑器 | TipTap | 基于 ProseMirror，扩展性强 |
| 可视化 | React Flow | 用于大纲树和知识图谱展示 |
| 状态管理 | Zustand | 轻量级，适合中小型应用 |
| 后端 | FastAPI | 快速开发，类型安全，异步原生 |
| ORM | SQLAlchemy 2.0 | 成熟稳定，async 支持 |
| 数据库 | PostgreSQL 16 | 关系型 + JSONB + pgvector |
| 向量库 | Qdrant | 轻量级，支持本地部署 |
| 缓存 | Redis | 会话、队列、缓存 |
| 任务队列 | Celery/Redis | 异步任务处理 |
| LLM SDK | OpenAI SDK (兼容模式) | 支持多模型切换 |

---

## 3. 核心领域模型

### 3.1 六级分层模型

```
Novel (作品)
├── WorldView (世界观) - 1:N
│   ├── MagicSystem (魔法体系)
│   ├── Geography (地理)
│   ├── History (历史)
│   └── Rules (规则)
├── Character (角色) - 1:N
│   ├── Profile (档案)
│   ├── Relationships (关系)
│   └── Arc (成长弧线)
├── Structure (结构) - 1:N
│   ├── Volume (卷)
│   ├── Arc (故事弧)
│   └── Chapter (章节)
├── Chapter (章节) - 1:N
│   ├── Scenes (场景列表)
│   └── Content (正文)
└── Scene (场景) - 1:N
    ├── Characters (参与角色)
    ├── Location (地点)
    ├── Events (事件)
    └── Content (内容)
```

### 3.2 三态修改机制

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Suggestion  │ →  │    Patch    │ →  │   Commit    │
│  (建议)      │    │   (补丁)     │    │   (提交)     │
└─────────────┘    └─────────────┘    └─────────────┘
     ↓                   ↓                   ↓
  草稿状态             预览状态            正式版本
  可编辑               可回滚              版本化
  可丢弃               影响分析            不可变
```

---

## 4. 模块设计

### 4.1 Backend 模块结构

```
backend/
├── app/
│   ├── api/                    # API 路由
│   │   ├── v1/
│   │   │   ├── projects.py
│   │   │   ├── characters.py
│   │   │   ├── chapters.py
│   │   │   ├── suggestions.py
│   │   │   └── agents.py
│   ├── core/                   # 核心配置
│   │   ├── config.py
│   │   ├── security.py
│   │   └── deps.py
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── novel.py
│   │   ├── character.py
│   │   ├── chapter.py
│   │   └── suggestion.py
│   ├── schemas/                # Pydantic 模式
│   │   ├── novel.py
│   │   ├── character.py
│   │   └── chapter.py
│   ├── services/               # 业务逻辑
│   │   ├── project_service.py
│   │   ├── character_service.py
│   │   ├── editor_service.py
│   │   └── agent_service.py
│   ├── agents/                 # Agent 编排
│   │   ├── base.py
│   │   ├── writing_orchestrator.py
│   │   ├── lore_agent.py
│   │   ├── character_agent.py
│   │   └── continuity_agent.py
│   └── db/                     # 数据库
│       ├── session.py
│       └── init_db.py
├── tests/
├── alembic/                    # 数据库迁移
├── pyproject.toml
└── requirements.txt
```

### 4.2 Frontend 模块结构

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   ├── components/
│   │   ├── editor/             # 编辑器组件
│   │   │   ├── NovelEditor.tsx
│   │   │   └── TipTapEditor.tsx
│   │   ├── knowledge/          # 知识图谱
│   │   │   └── KnowledgeGraph.tsx
│   │   ├── outline/            # 大纲树
│   │   │   └── OutlineTree.tsx
│   │   └── dashboard/          # 仪表盘
│   ├── features/               # 功能模块
│   │   ├── projects/
│   │   ├── characters/
│   │   └── chapters/
│   ├── hooks/                  # 自定义 Hooks
│   ├── store/                  # Zustand 状态
│   ├── services/               # API 客户端
│   ├── types/                  # TypeScript 类型
│   └── lib/                    # 工具函数
├── public/
├── package.json
└── tsconfig.json
```

---

## 5. Agent 编排架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Writing Orchestrator                        │
│                    (主编排器)                                 │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ↓                    ↓                    ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Lore Agent   │    │ Character     │    │  Outline      │
│  (设定维护)   │    │ Agent         │    │  Agent        │
│               │    │ (角色一致性)  │    │  (大纲生成)   │
└───────────────┘    └───────────────┘    └───────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ↓
                    ┌───────────────┐
                    │   Draft       │
                    │   Agent       │
                    │  (正文生成)   │
                    └───────────────┘
                              ↓
                    ┌───────────────┐
                    │  Continuity   │
                    │  Agent        │
                    │ (连续性检查)  │
                    └───────────────┘
```

---

## 6. 数据流设计

### 6.1 修改传播流程

```
用户修改对象
    ↓
ImpactAnalyzer.analyze()
    ↓
构建依赖图 (Dependency Graph)
    ↓
拓扑排序受影响节点
    ↓
并行生成 Suggestion
    ↓
用户确认 → Patch → Commit
```

### 6.2 AI 写作流程

```
用户请求 (Context + Instruction)
    ↓
WritingOrchestrator.plan()
    ↓
分解为子任务
    ↓
分配给 Specialist Agents
    ↓
收集结果 → Continuity.check()
    ↓
生成 Suggestion
    ↓
用户确认后 Apply
```

---

## 7. 关键技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 后端框架 | FastAPI | Python AI 生态好，异步原生，开发效率高 |
| 前端框架 | Next.js | SSR/SSG 支持，React 生态成熟 |
| 编辑器 | TipTap | 基于 ProseMirror，架构清晰，扩展方便 |
| 向量存储 | Qdrant | 轻量级，易于部署，性能好 |
| 任务队列 | Celery + Redis | 成熟方案，支持定时和重试 |
| 模型接入 | OpenAI SDK 兼容层 | 统一接口，便于切换模型 |

---

## 8. MVP 范围

第一阶段 MVP 包含：

1. **项目管理**：创建/编辑小说项目
2. **角色管理**：CRUD + 关系图
3. **世界观**：基础设定库
4. **章节编辑**：富文本编辑器
5. **AI 对话**：基于上下文的对话接口
6. **Suggestion 机制**：建议-预览-确认流程

**不包含**（留待 V2）：
- GraphRAG 高级检索
- 复杂的影响分析可视化
- 多用户协作
- 实时协同编辑

---

## 9. 非功能性需求

| 需求 | 指标 |
|------|------|
| 响应时间 | API < 200ms (P95) |
| 并发用户 | 100+ (MVP) |
| 数据持久性 | 99.9% |
| 可扩展性 | 服务无状态，可水平扩展 |

---

## 10. 数据库设计概要

### 10.1 核心表结构

```sql
-- 项目表
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    genre VARCHAR(100),
    target_audience VARCHAR(100),
    target_word_count INTEGER,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 人物表
CREATE TABLE characters (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    name VARCHAR(255) NOT NULL,
    profile JSONB,
    relationships JSONB,
    arc_state JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 世界观设定表
CREATE TABLE world_settings (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    category VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 章节表
CREATE TABLE chapters (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    volume_id UUID,
    chapter_number INTEGER,
    title VARCHAR(255),
    outline TEXT,
    content TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 场景表
CREATE TABLE scenes (
    id UUID PRIMARY KEY,
    chapter_id UUID REFERENCES chapters(id),
    scene_order INTEGER,
    pov_character_id UUID REFERENCES characters(id),
    location VARCHAR(255),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 建议表（三态机制）
CREATE TABLE suggestions (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    target_type VARCHAR(50),
    target_id UUID,
    type VARCHAR(50),
    content JSONB,
    status VARCHAR(50), -- draft, patch, committed, discarded
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 版本快照表
CREATE TABLE snapshots (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 11. API 设计概要

### 11.1 项目相关

```
POST   /api/v1/projects              # 创建项目
GET    /api/v1/projects              # 获取项目列表
GET    /api/v1/projects/{id}         # 获取项目详情
PUT    /api/v1/projects/{id}         # 更新项目
DELETE /api/v1/projects/{id}         # 删除项目
POST   /api/v1/projects/{id}/snapshot # 创建快照
```

### 11.2 人物相关

```
POST   /api/v1/projects/{id}/characters      # 创建人物
GET    /api/v1/projects/{id}/characters      # 获取人物列表
GET    /api/v1/characters/{id}               # 获取人物详情
PUT    /api/v1/characters/{id}               # 更新人物
DELETE /api/v1/characters/{id}               # 删除人物
GET    /api/v1/characters/{id}/relationships # 获取关系图
```

### 11.3 章节相关

```
POST   /api/v1/projects/{id}/chapters        # 创建章节
GET    /api/v1/projects/{id}/chapters        # 获取章节列表
GET    /api/v1/chapters/{id}                 # 获取章节详情
PUT    /api/v1/chapters/{id}                 # 更新章节
DELETE /api/v1/chapters/{id}                 # 删除章节
GET    /api/v1/chapters/{id}/scenes          # 获取场景列表
```

### 11.4 AI Agent 相关

```
POST   /api/v1/agents/chat                   # 对话
POST   /api/v1/agents/suggest                # 生成建议
POST   /api/v1/agents/analyze-impact         # 影响分析
POST   /api/v1/agents/check-continuity       # 连续性检查
```

### 11.5 Suggestion 相关

```
POST   /api/v1/suggestions                   # 创建建议
GET    /api/v1/suggestions/{id}              # 获取建议详情
PUT    /api/v1/suggestions/{id}/patch        # 转为补丁
POST   /api/v1/suggestions/{id}/commit       # 提交应用
DELETE /api/v1/suggestions/{id}              # 丢弃建议
```

---

## 12. 开发环境配置

### 12.1 后端依赖

```toml
# pyproject.toml
[project]
name = "ai-novel-agent-backend"
version = "0.1.0"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "redis>=5.0.0",
    "celery>=5.3.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "alembic>=1.13.0",
    "openai>=1.0.0",
    "qdrant-client>=1.7.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.6",
]
```

### 12.2 前端依赖

```json
{
  "name": "ai-novel-agent-frontend",
  "version": "0.1.0",
  "dependencies": {
    "next": "14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tiptap/react": "^2.1.0",
    "@tiptap/starter-kit": "^2.1.0",
    "reactflow": "^11.10.0",
    "zustand": "^4.4.0",
    "axios": "^1.6.0",
    "zod": "^3.22.0"
  }
}
```

---

## 13. 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx / Traefik                       │
│                         (反向代理)                            │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ↓                              ↓
┌─────────────────┐          ┌─────────────────┐
│   Frontend      │          │   Backend       │
│   (Next.js)     │          │   (FastAPI)     │
│   Static/SSR    │          │   Multi-instance│
└─────────────────┘          └─────────────────┘
                                      │
         ┌─────────────┬──────────────┼──────────────┬─────────────┐
         ↓             ↓              ↓              ↓             ↓
    ┌─────────┐  ┌─────────┐   ┌─────────┐  ┌─────────┐  ┌─────────┐
    │PostgreSQL│  │ Qdrant  │   │  Redis  │  │ Celery  │  │  LLM API │
    │ (主库)   │  │ (向量)  │   │ (缓存)  │  │ (Worker)│  │  (模型)  │
    └─────────┘  └─────────┘   └─────────┘  └─────────┘  └─────────┘
```

---

## 14. 安全设计

### 14.1 认证与授权

- JWT Token 认证
- 基于项目的访问控制（项目成员机制）
- API 密钥支持（用于未来 API 开放）

### 14.2 数据安全

- 敏感数据加密存储
- HTTPS 强制传输
- SQL 注入防护（ORM 参数化查询）
- XSS 防护（前端转义）

### 14.3 限流与防护

- API 速率限制（按用户/IP）
- 请求体大小限制
- CORS 配置

---

## 15. 测试策略

### 15.1 后端测试

- 单元测试（pytest + pytest-asyncio）
- API 集成测试（fastapi TestClient）
- Agent 行为测试（Mock LLM 响应）

### 15.2 前端测试

- 组件测试（Vitest + React Testing Library）
- E2E 测试（Playwright）

---

## 16. 监控与日志

### 16.1 日志

- 结构化日志（JSON 格式）
- 日志级别：DEBUG/INFO/WARNING/ERROR
- 关键操作审计日志

### 16.2 监控指标

- API 响应时间
- Agent 调用次数与延迟
- 数据库查询性能
- Redis 缓存命中率

---

## 17. 后续演进方向

### 17.1 V2 计划

- GraphRAG 高级检索
- 复杂影响分析可视化
- 人物弧光追踪器
- 时间线视图

### 17.2 V3 计划

- 多用户协作
- 实时协同编辑（Y.js）
- 文风克隆
- 跨媒介资产转换

---

## 附录：架构决策记录（ADR）

### ADR-001: 选择 FastAPI 而非 NestJS

**状态**: 已接受

**背景**: 后端框架需要在 Python（AI 生态）和 TypeScript（类型安全）之间选择。

**决策**: 选择 FastAPI

**理由**:
1. Python 拥有更丰富的 AI/ML 生态
2. FastAPI 原生异步支持
3. Pydantic 提供优秀的类型验证
4. 开发效率高，学习曲线平缓

### ADR-002: 选择 TipTap 而非 Lexical

**状态**: 已接受

**背景**: 富文本编辑器需要在 TipTap 和 Lexical 之间选择。

**决策**: 选择 TipTap

**理由**:
1. 基于 ProseMirror，架构更成熟
2. 社区更活跃，插件更丰富
3. 文档更完善
4. 与 Vue/React 都有良好支持

### ADR-003: 选择 Qdrant 而非 Pinecone

**状态**: 已接受

**背景**: 向量数据库需要考虑成本、部署难度和性能。

**决策**: 选择 Qdrant

**理由**:
1. 支持本地部署，成本可控
2. 性能优秀，延迟低
3. 支持过滤和混合搜索
4. 开源，可定制性强
