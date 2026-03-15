# AI 超长篇小说写作 Agent - 技术架构设计

> 当前实现说明：仓库已经以项目级 `thread / run / operation` 作为公开 Agent 工作流接口，并在其上加入了项目级 profile、subtask、风险分级、verification 与 checkpoint 基础设施。后续多子代理、权限分层、完成校验深化与上下文压缩的演进路线，以 [IMPLEMENTATION_PLAN.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/IMPLEMENTATION_PLAN.md) 为准。本文件继续保留“目标架构”视角。

## 文档信息
- 项目名称：AI 超长篇小说写作 Agent 应用
- 文档类型：技术架构文档（TECH_ARCH）
- 版本：v1.1
- 状态：修订版
- 创建日期：2026-03-11
- 更新日期：2026-03-12

> 兼容说明：本文件中部分目录示意早于当前代码实现。当前仓库实际结构、开发命令和测试状态以 `README.md`、`docs/STATUS.md`、`docs/DEVELOPMENT.md` 为准。

---

## 1. 整体架构

采用 **前后端分离 + 单体应用演进** 架构（MVP 阶段不采用微服务）：

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
│                     Backend (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Auth Middleware │ CORS │ Request Validation │ Error    │   │
│  │  Handler                                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────────┐  │
│  │ Project   │ │ Knowledge │ │ Editor    │ │ Agent           │  │
│  │ Service   │ │ Service   │ │ Service   │ │ Orchestrator    │  │
│  └───────────┘ └───────────┘ └───────────┘ └─────────────────┘  │
│  ┌───────────┐ ┌───────────┐ ┌─────────────────────────────────┐ │
│  │ Suggestion│ │ Impact    │ │ Continuity &                    │ │
│  │ Service   │ │ Analyzer  │ │ Memory Service                  │ │
│  └───────────┘ └───────────┘ └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          ↓              ↓              ↓                ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ PostgreSQL  │ │  pgvector   │ │   Redis     │ │  LLM API    │
│ (主数据+    │ │ (向量扩展)  │ │ (缓存/队列) │ │  (模型网关)  │
│  向量存储)   │ │             │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

> **架构演进说明**：MVP 阶段使用单体 FastAPI 应用 + PostgreSQL + pgvector 扩展进行向量存储。V2 阶段可根据规模需求演进为微服务架构，并将向量存储迁移至专用向量数据库（Qdrant/Pinecone）。

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
| 数据库 | PostgreSQL 16 + pgvector | 关系型 + JSONB + 向量检索一体化 |
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
  status=draft       status=patched      status=committed
  草稿状态             预览状态            正式版本
  可编辑               可回滚              版本化
  可丢弃               影响分析            不可变
```

**状态枚举定义**：
```python
class SuggestionStatus(str, Enum):
    DRAFT = "draft"           # 草稿：AI 生成的初始建议
    PATCHED = "patched"       # 补丁：用户确认后转为预览状态
    COMMITTED = "committed"   # 已提交：已应用到目标对象
    DISCARDED = "discarded"   # 已丢弃：用户拒绝的建议
```

---

## 4. 模块设计

### 4.1 Backend 目录结构（MVP 最小落地版）

```
backend/
├── app/
│   ├── api/                    # API 路由
│   │   ├── __init__.py
│   │   ├── deps.py             # 依赖注入（当前用户、DB session）
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # 认证相关（MVP: 简单 API key）
│   │   │   ├── projects.py     # 项目 CRUD
│   │   │   ├── characters.py   # 人物 CRUD
│   │   │   ├── world_settings.py   # 世界观 CRUD
│   │   │   ├── chapters.py     # 章节 CRUD
│   │   │   ├── scenes.py       # 场景 CRUD
│   │   │   ├── suggestions.py  # 建议/补丁/提交
│   │   │   ├── agents.py       # Agent 对话与执行
│   │   │   └── analysis.py     # 影响分析、连续性检查
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py           # 环境配置
│   │   ├── security.py         # 安全相关（MVP: 简化版）
│   │   └── logging.py          # 日志配置
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── base.py             # Base 类
│   │   ├── project.py          # 项目模型
│   │   ├── character.py        # 人物模型
│   │   ├── world_setting.py    # 世界观模型
│   │   ├── chapter.py          # 章节模型
│   │   ├── scene.py            # 场景模型
│   │   ├── suggestion.py       # 建议模型
│   │   ├── memory.py           # 记忆/向量模型
│   │   └── user.py             # 用户模型（MVP: 简化）
│   ├── schemas/                # Pydantic 模式
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── character.py
│   │   ├── world_setting.py
│   │   ├── chapter.py
│   │   ├── scene.py
│   │   ├── suggestion.py
│   │   ├── agent.py
│   │   └── analysis.py
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── project_service.py
│   │   ├── character_service.py
│   │   ├── world_setting_service.py
│   │   ├── chapter_service.py
│   │   ├── scene_service.py
│   │   ├── suggestion_service.py
│   │   ├── memory_service.py   # 记忆抽取与检索
│   │   └── llm_service.py      # LLM 调用统一入口
│   ├── agents/                 # Agent 编排层
│   │   ├── __init__.py
│   │   ├── base.py             # Agent 基类
│   │   ├── orchestrator.py     # Writing Orchestrator
│   │   ├── lore_agent.py       # 世界观 Agent
│   │   ├── character_agent.py  # 人物 Agent
│   │   ├── outline_agent.py    # 大纲 Agent
│   │   ├── draft_agent.py      # 正文生成 Agent
│   │   └── continuity_agent.py # 连续性检查 Agent
│   ├── db/                     # 数据库
│   │   ├── __init__.py
│   │   ├── session.py          # DB session 工厂
│   │   └── init_db.py          # 初始化脚本
│   └── main.py                 # FastAPI 应用入口
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest 配置
│   ├── test_api/               # API 测试
│   ├── test_services/          # 服务层测试
│   └── test_agents/            # Agent 测试（Mock LLM）
├── alembic/                    # 数据库迁移
│   ├── versions/
│   └── env.py
├── scripts/                    # 工具脚本
│   ├── init_db.sh
│   └── seed_data.py
├── pyproject.toml
└── requirements.txt
```

### 4.2 Frontend 目录结构（MVP 最小落地版）

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # 根布局
│   │   ├── page.tsx            # 首页
│   │   ├── dashboard/          # 仪表盘
│   │   │   └── page.tsx
│   │   ├── projects/           # 项目页面
│   │   │   ├── [id]/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── characters/
│   │   │   │   ├── world-settings/
│   │   │   │   └── chapters/
│   │   │   └── new/page.tsx
│   │   └── api/                # API Route（如有需要）
│   ├── components/
│   │   ├── common/             # 通用组件
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   └── Modal.tsx
│   │   ├── editor/             # 编辑器组件
│   │   │   ├── NovelEditor.tsx
│   │   │   └── TipTapEditor.tsx
│   │   ├── knowledge/          # 知识图谱
│   │   │   └── KnowledgeGraph.tsx
│   │   ├── outline/            # 大纲树
│   │   │   └── OutlineTree.tsx
│   │   ├── agent/              # Agent 对话组件
│   │   │   └── AgentChatPanel.tsx
│   │   └── dashboard/          # 仪表盘组件
│   ├── features/               # 功能模块（业务逻辑）
│   │   ├── projects/
│   │   ├── characters/
│   │   ├── world-settings/
│   │   └── chapters/
│   ├── hooks/                  # 自定义 Hooks
│   │   ├── useAgent.ts
│   │   ├── useSuggestions.ts
│   │   └── useEditor.ts
│   ├── store/                  # Zustand 状态
│   │   ├── projectStore.ts
│   │   ├── editorStore.ts
│   │   └── agentStore.ts
│   ├── services/               # API 客户端
│   │   ├── api.ts              # axios 实例
│   │   ├── projects.ts
│   │   ├── characters.ts
│   │   └── agents.ts
│   ├── types/                  # TypeScript 类型
│   │   ├── project.ts
│   │   ├── character.ts
│   │   └── agent.ts
│   ├── lib/                    # 工具函数
│   │   └── utils.ts
│   └── styles/                 # 样式
│       └── globals.css
├── public/
├── package.json
├── tsconfig.json
├── next.config.mjs
└── tailwind.config.ts
```

---

## 5. Agent 编排架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Writing Orchestrator                        │
│                    (主编排器)                                 │
│            接收用户请求 → 任务分解 → Agent 调度               │
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
                              ↓
                    ┌───────────────┐
                    │   输出        │
                    │  Suggestion   │
                    └───────────────┘
```

### Agent 职责定义

| Agent | 输入 | 输出 | 调用时机 |
|-------|------|------|---------|
| Writing Orchestrator | 用户请求 + 当前上下文 | 任务分解 + Agent 调度计划 | 所有 Agent 请求的入口 |
| Lore Agent | 世界观设定 + 修改指令 | 设定补丁 + 影响范围 | 修改世界观时 |
| Character Agent | 人物档案 + 修改指令 | 人设补丁 + 关系影响 | 修改人物时 |
| Outline Agent | 结构 + 生成指令 | 大纲/场景卡 | 生成/修改大纲时 |
| Draft Agent | 场景参数 + 风格要求 | 正文内容 | 生成/改写正文时 |
| Continuity Agent | 章节/对象 | 一致性问题报告 | 提交前检查时 |

---

## 6. 关键时序图

### 6.1 Suggestion 创建到提交流程

```
用户              Frontend           API              Service         Agent        DB
 │                    │                 │                 │              │           │
 │─生成建议───────────>│                 │                 │              │           │
 │                    │─POST /agents/suggest─────────────>│              │           │
 │                    │                 │                 │─调用─────────>│           │
 │                    │                 │                 │              │─查询上下文─>│
 │                    │                 │                 │<─────────────│           │
 │                    │<────────────────返回 Suggestion (draft)────────────│           │
 │<─显示预览──────────│                 │                 │              │           │
 │─确认转为 Patch────>│                 │                 │              │           │
 │                    │─PUT /suggestions/{id}/patch─────>│              │           │
 │                    │                 │                 │─影响分析─────>│           │
 │                    │<────────────────返回 Patch 详情───────────────────│           │
 │<─显示影响分析──────│                 │                 │              │           │
 │─确认提交──────────>│                 │                 │              │           │
 │                    │─POST /suggestions/{id}/commit───>│              │           │
 │                    │                 │                 │─应用修改─────>│           │
 │                    │                 │                 │              │─更新──────>│
 │                    │<────────────────成功─────────────────────────────│           │
 │<─更新完成──────────│                 │                 │              │           │
```

### 6.2 影响分析流程

```
ImpactAnalyzer.analyze()
    ↓
1. 获取修改对象及其依赖关系
    ↓
2. 构建依赖图 (Dependency Graph)
    ↓
3. 拓扑排序受影响节点
    ↓
4. 批量生成 Suggestion（并行）
    ↓
5. 聚合影响报告
    ↓
返回：受影响对象列表 + 风险等级 + 修复建议
```

---

## 7. 失败处理与回滚策略

### 7.1 LLM 调用失败

| 场景 | 处理策略 |
|------|---------|
| 超时 | 3 次指数退避重试，每次 timeout × 2 |
| 限流 | 自动排队到 Celery，稍后重试 |
| 内容审核失败 | 返回明确错误信息，不生成 Suggestion |
| 格式解析失败 | 记录日志，返回友好错误，请求重新生成 |

### 7.2 数据库操作失败

| 场景 | 处理策略 |
|------|---------|
| 事务冲突 | 自动重试 3 次 |
| 外键约束冲突 | 回滚事务，返回详细错误信息 |
| 连接失败 | 返回服务不可用，触发告警 |

### 7.3 Suggestion 回滚

```python
# 回滚策略
class RollbackStrategy:
    def rollback(self, suggestion_id: str) -> bool:
        # 1. 获取 Suggestion 对应的 Commit 记录
        # 2. 从快照恢复数据
        # 3. 验证数据完整性
        # 4. 创建反向 Commit 记录
        pass
```

---

## 8. 数据库设计

### 8.1 核心表结构

```sql
-- 扩展 PostgreSQL 启用 pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 用户表（MVP 简化版）
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    api_key_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 项目表
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    genre VARCHAR(100),
    target_audience VARCHAR(100),
    target_word_count INTEGER,
    status VARCHAR(50) DEFAULT 'draft', -- drafting, writing, revising, completed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 人物表
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    profile JSONB DEFAULT '{}',
    relationships JSONB DEFAULT '{}',
    arc_state JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 世界观设定表
CREATE TABLE world_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    category VARCHAR(100), -- magic_system, geography, history, etc.
    name VARCHAR(255) NOT NULL,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 卷表
CREATE TABLE volumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    volume_number INTEGER,
    title VARCHAR(255),
    outline TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 章节表
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    volume_id UUID REFERENCES volumes(id) ON DELETE SET NULL,
    chapter_number INTEGER,
    title VARCHAR(255),
    outline TEXT,
    content TEXT,
    status VARCHAR(50) DEFAULT 'draft', -- draft, writing, completed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, volume_id, chapter_number)
);

-- 场景表
CREATE TABLE scenes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    scene_order INTEGER,
    pov_character_id UUID REFERENCES characters(id),
    location VARCHAR(255),
    content TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 建议表（三态机制）
CREATE TABLE suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL, -- character, world_setting, chapter, scene
    target_id UUID NOT NULL,
    type VARCHAR(50) NOT NULL, -- character_edit, world_edit, content_gen, etc.
    content JSONB NOT NULL, -- 建议的具体内容
    status VARCHAR(50) NOT NULL DEFAULT 'draft', -- draft, patched, committed, discarded
    impact_analysis JSONB, -- 影响分析结果
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    committed_at TIMESTAMP
);

-- 版本快照表（用于回滚）
CREATE TABLE snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 记忆表（向量存储 + pgvector）
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL, -- episode, semantic, fact
    content TEXT NOT NULL,
    embedding vector(<configured_dimension>), -- 由 EMBEDDING_DIMENSION 决定
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建向量索引用于相似度检索
CREATE INDEX memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX memories_project_type_idx ON memories(project_id, memory_type);

-- 依赖关系表（用于影响分析）
CREATE TABLE dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    dependency_type VARCHAR(50), -- references, influences, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, source_type, source_id, target_type, target_id)
);

CREATE INDEX dependencies_source_idx ON dependencies(project_id, source_type, source_id);
CREATE INDEX dependencies_target_idx ON dependencies(project_id, target_type, target_id);
```

### 8.2 MVP 阶段向量存储说明

**PostgreSQL + pgvector 方案**（MVP 首选）：
- 使用 `memories` 表存储结构化记忆与向量嵌入
- 利用 ivfflat 索引进行高效余弦相似度搜索
- 优势：减少基础设施复杂度，单数据库事务一致性，降低运维成本
- 劣势：向量检索性能不如专用向量数据库（但 MVP 规模可接受）

**V2 演进方向**：
- 当数据量 > 100 万条向量或并发 QPS > 100 时
- 迁移至 Qdrant 专用向量数据库
- PostgreSQL 仅保留元数据和关系数据

---

## 9. API 设计

### 9.1 认证相关（MVP 简化版）

```
POST   /api/v1/auth/register           # 注册用户
POST   /api/v1/auth/login              # 登录获取 token
POST   /api/v1/auth/api-key            # 生成 API key
```

> MVP 阶段说明：暂不实现复杂的项目成员机制、多用户协作。一个项目属于一个用户。认证简化为 API key 或简单 JWT。

### 9.2 项目相关

```
POST   /api/v1/projects                # 创建项目
GET    /api/v1/projects                # 获取项目列表
GET    /api/v1/projects/{id}           # 获取项目详情
PUT    /api/v1/projects/{id}           # 更新项目
DELETE /api/v1/projects/{id}           # 删除项目
POST   /api/v1/projects/{id}/snapshot  # 创建快照
GET    /api/v1/projects/{id}/snapshots # 获取快照列表
POST   /api/v1/projects/{id}/rollback  # 回滚到快照
```

### 9.3 人物相关

```
POST   /api/v1/projects/{id}/characters        # 创建人物
GET    /api/v1/projects/{id}/characters        # 获取人物列表
GET    /api/v1/characters/{id}                 # 获取人物详情
PUT    /api/v1/characters/{id}                 # 更新人物
DELETE /api/v1/characters/{id}                 # 删除人物
GET    /api/v1/characters/{id}/relationships   # 获取关系图
```

### 9.4 世界观相关

```
POST   /api/v1/projects/{id}/world-settings    # 创建设定
GET    /api/v1/projects/{id}/world-settings    # 获取设定列表
GET    /api/v1/world-settings/{id}             # 获取设定详情
PUT    /api/v1/world-settings/{id}             # 更新设定
DELETE /api/v1/world-settings/{id}             # 删除设定
```

### 9.5 章节相关

```
POST   /api/v1/projects/{id}/volumes           # 创建卷
POST   /api/v1/volumes/{id}/chapters           # 创建章节
GET    /api/v1/volumes/{id}/chapters           # 获取章节列表
GET    /api/v1/chapters/{id}                   # 获取章节详情
PUT    /api/v1/chapters/{id}                   # 更新章节
DELETE /api/v1/chapters/{id}                   # 删除章节
POST   /api/v1/chapters/{id}/scenes            # 创建场景
GET    /api/v1/chapters/{id}/scenes            # 获取场景列表
```

### 9.6 AI Agent 相关

```
POST   /api/v1/agents/chat                     # 对话
POST   /api/v1/agents/suggest                  # 生成建议
POST   /api/v1/agents/analyze-impact           # 影响分析
POST   /api/v1/agents/check-continuity         # 连续性检查
POST   /api/v1/agents/generate-outline         # 生成大纲
POST   /api/v1/agents/generate-content         # 生成内容
```

### 9.7 Suggestion 相关

```
GET    /api/v1/projects/{id}/suggestions       # 获取建议列表
GET    /api/v1/suggestions/{id}                # 获取建议详情
PUT    /api/v1/suggestions/{id}/patch          # 转为补丁（执行影响分析）
POST   /api/v1/suggestions/{id}/commit         # 提交应用
DELETE /api/v1/suggestions/{id}                # 丢弃建议
```

### 9.8 导出相关

```
GET    /api/v1/projects/{id}/export/txt        # 导出 TXT
GET    /api/v1/projects/{id}/export/markdown   # 导出 Markdown
GET    /api/v1/projects/{id}/export/docx       # 导出 DOCX
```

---

## 10. 关键技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 后端框架 | FastAPI | Python AI 生态好，异步原生，开发效率高 |
| 前端框架 | Next.js | SSR/SSG 支持，React 生态成熟 |
| 编辑器 | TipTap | 基于 ProseMirror，架构清晰，扩展方便 |
| 向量存储（MVP） | PostgreSQL + pgvector | 单库简化部署，事务一致性，降低运维成本 |
| 任务队列 | Celery + Redis | 成熟方案，支持定时和重试 |
| 模型接入 | OpenAI SDK 兼容层 | 统一接口，便于切换模型 |
| 认证（MVP） | 简单 API Key | MVP 阶段单人使用，暂不需要复杂权限系统 |

---

## 11. 非功能性需求

| 需求 | 指标 |
|------|------|
| API 响应时间 | < 200ms (P95) 非生成类操作 |
| LLM 生成响应 | 首次响应 < 3s，流式输出 |
| 并发用户 | 50+ (MVP) |
| 数据持久性 | 99.9% |
| 可扩展性 | 服务无状态，可水平扩展 |
| 可观测性 | 结构化日志 + 关键指标监控 |

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
    "pgvector>=0.2.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.25.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
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
    "@tiptap/extension-collaboration": "^2.1.0",
    "reactflow": "^11.10.0",
    "zustand": "^4.4.0",
    "axios": "^1.6.0",
    "zod": "^3.22.0",
    "tailwindcss": "^3.3.0",
    "@radix-ui/react-dialog": "^1.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "typescript": "^5.0.0",
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0"
  }
}
```

---

## 13. 部署架构（MVP）

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx / Traefik                       │
│                         (反向代理 + SSL)                      │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ↓                              ↓
┌─────────────────┐          ┌─────────────────┐
│   Frontend      │          │   Backend       │
│   (Next.js)     │          │   (FastAPI)     │
│   Static/SSR    │          │   Multi-instance│
│   Docker容器    │          │   Docker容器    │
└─────────────────┘          └─────────────────┘
                                      │
         ┌─────────────┬──────────────┼──────────────┬─────────────┐
         ↓             ↓              ↓              ↓             ↓
    ┌─────────┐  ┌─────────┐   ┌─────────┐  ┌─────────┐  ┌─────────┐
    │PostgreSQL│  │  Redis  │   │  Celery │  │  LLM API │  │ pgvector│
    │ (主库)   │  │ (缓存)  │   │ (Worker)│  │  (模型)  │  │ (扩展)  │
    │Docker容器│  │Docker容器│   │Docker容器│  │ (外部)   │  │ (同库)  │
    └─────────┘  └─────────┘   └─────────┘  └─────────┘  └─────────┘
```

### Docker Compose 配置（简化版）

```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: novel_agent
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql+asyncpg://user:password@postgres/novel_agent
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "3000:3000"

  celery_worker:
    build: ./backend
    command: celery -A app.workers worker --loglevel=info
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

---

## 14. 测试策略

### 14.1 后端测试

- **单元测试**：pytest + pytest-asyncio
  - Service 层业务逻辑测试
  - Schema 验证测试
- **API 集成测试**：fastapi TestClient
  - 端到端 API 调用测试
  - 认证/授权测试
- **Agent 测试**：Mock LLM 响应
  - 验证 Agent 调用逻辑
  - 验证 Suggestion 生成流程

### 14.2 前端测试

- **组件测试**：Vitest + React Testing Library
- **E2E 测试**：Playwright（可选，MVP 后期补充）

---

## 15. 监控与日志

### 15.1 日志规范

```python
import structlog

logger = structlog.get_logger()

# 示例
logger.info("agent_call",
            agent_type="lore_agent",
            project_id=project_id,
            latency_ms=elapsed)
```

### 15.2 关键指标

- API 响应时间（P50/P95/P99）
- Agent 调用次数与延迟
- LLM Token 消耗
- 数据库查询性能
- Redis 缓存命中率
- Suggestion 转化率（draft → patched → committed）

---

## 16. 安全设计（MVP 简化版）

### 16.1 认证

- API Key 认证（主要方式）
- 可选 JWT Token（用于 Web UI）

### 16.2 数据安全

- HTTPS 强制传输
- SQL 注入防护（ORM 参数化查询）
- XSS 防护（前端转义）
- API Key 哈希存储

### 16.3 限流

- API 速率限制（按 API key）
- 请求体大小限制
- CORS 配置

> MVP 阶段不实现复杂的项目成员权限控制。一个项目属于一个用户。

---

## 17. 后续演进方向

### 17.1 V2 计划

- GraphRAG 高级检索（迁移向量存储至 Qdrant）
- 复杂影响分析可视化
- 人物弧光追踪器
- 时间线视图
- 伏笔账本

### 17.2 V3 计划

- 多用户协作（项目成员机制）
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

### ADR-003: MVP 使用 PostgreSQL + pgvector 而非独立向量数据库

**状态**: 已接受

**背景**: 向量存储需要在 Qdrant/Pinecone 和 pgvector 之间选择。

**决策**: MVP 选择 pgvector，V2 评估迁移至 Qdrant

**理由**:
1. 减少 MVP 基础设施复杂度
2. 单数据库事务一致性
3. 降低部署和运维成本
4. MVP 规模数据量下性能可接受
5. 未来可无缝迁移至专用向量数据库

### ADR-004: MVP 简化认证，暂不实现项目成员机制

**状态**: 已接受

**背景**: MVP 需要在功能完整性和快速落地之间平衡。

**决策**: MVP 仅实现简单 API Key 认证，一人一项目，暂不实现多用户协作

**理由**:
1. MVP 核心价值是 Agent 写作能力，而非协作
2. 简化权限系统降低开发成本
3. 多用户协作可留待 V3 实现
4. 单用户模式满足早期创作者需求
