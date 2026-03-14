# AI Novel Agent

AI 驱动的超长篇小说写作助手，通过多 Agent 协作帮助作者构思、规划和撰写长篇小说。

## 功能概览

- **项目管理** - 创建和管理多个小说项目，设置题材、受众、目标字数
- **人物管理** - 创建角色档案，定义性格、背景、关系网络
- **世界观构建** - 管理魔法体系、地理、历史、组织等设定
- **章节与场景** - 分卷/章/场景三级结构组织小说内容
- **AI 写作助手** - 5 个专业 Agent 分别负责世界观、人物、大纲、写作、连续性检查
- **三态修改机制** - AI 建议 → 确认 → 应用，每步可回退
- **记忆系统** - 自动提取叙事事实，向量嵌入检索相关上下文
- **导出** - 支持 TXT 和 Markdown 格式导出

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 + PostgreSQL + pgvector |
| 前端 | Next.js 15 (App Router) + TypeScript + Tailwind CSS + Zustand |
| AI | OpenAI SDK 兼容模式（支持 DeepSeek、SiliconFlow 等） |
| 部署 | Docker Compose |

## 快速开始

### 前置要求

- Docker & Docker Compose
- LLM API Key（DeepSeek、OpenAI 或其他兼容服务）
- Embedding API Key（SiliconFlow、OpenAI 或其他兼容服务）

### 启动

```bash
# 1. 克隆项目
git clone <repo-url>
cd ai-novel-agent

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，配置 LLM 和 Embedding（见下方说明）

# 3. 启动所有服务
cd infra && docker-compose up -d

# 或者本地开发：
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 环境变量配置

编辑 `backend/.env`，配置 LLM（对话生成）和 Embedding（向量嵌入）两个服务。两者支持不同提供商，只要兼容 OpenAI SDK 接口即可。

```bash
# ---- LLM 对话生成 ----
LLM_API_KEY=sk-xxx              # API Key
LLM_BASE_URL=https://api.deepseek.com   # API 地址
LLM_MODEL=deepseek-chat         # 模型名称
MAX_TOKENS=4096                 # 最大生成 token 数
TEMPERATURE=0.7                 # 采样温度

# ---- Embedding 向量嵌入 ----
EMBEDDING_API_KEY=sk-xxx                     # API Key（留空则复用 LLM_API_KEY）
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1  # API 地址（留空则复用 LLM_BASE_URL）
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B     # 模型名称
```

**常见配置示例：**

| 用途 | 提供商 | `BASE_URL` | 推荐模型 |
|------|--------|-----------|----------|
| LLM 对话 | DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |
| LLM 对话 | OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Embedding | SiliconFlow | `https://api.siliconflow.cn/v1` | `Qwen/Qwen3-Embedding-8B` |
| Embedding | OpenAI | `https://api.openai.com/v1` | `text-embedding-3-small` |

> 如果 LLM 和 Embedding 使用同一个提供商，可以只填 `LLM_*` 配置，`EMBEDDING_*` 留空即可自动复用。

### 访问

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 项目结构

```
ai-novel-agent/
├── backend/
│   └── app/
│       ├── agents/          # AI Agent 层（5个专业Agent + Orchestrator）
│       ├── api/v1/          # FastAPI 路由（70+ 端点）
│       ├── models/          # SQLAlchemy 模型（10个表）
│       ├── schemas/         # Pydantic 请求/响应模式
│       ├── services/        # 业务逻辑层
│       ├── core/            # 配置、异常
│       └── db/              # 数据库会话
├── frontend/
│   ├── app/                 # Next.js 页面（21个路由）
│   ├── components/          # React 组件
│   └── lib/                 # API客户端、状态管理、类型
├── infra/                   # Docker Compose 配置
└── docs/                    # PRD、技术架构、实施计划
```

## AI Agent 架构

```
用户消息 → WritingOrchestrator（LLM 意图分类）
                ├── LoreAgent        世界观设定
                ├── CharacterAgent   人物塑造
                ├── OutlineAgent     大纲规划
                ├── DraftAgent       正文写作
                └── ContinuityAgent  连续性检查
                        ↓
                  Suggestion（三态修改）
                  draft → patched → committed
```

## API 端点

### 核心 CRUD
- `POST/GET/PATCH/DELETE` `/api/v1/projects` - 项目
- `POST/GET/PATCH/DELETE` `/api/v1/characters` - 人物
- `POST/GET/PATCH/DELETE` `/api/v1/world-settings` - 世界观
- `POST/GET/PATCH/DELETE` `/api/v1/chapters` - 章节
- `POST/GET/PATCH/DELETE` `/api/v1/scenes` - 场景

### AI Agent
- `POST /api/v1/agent/chat` - AI 对话
- `POST /api/v1/agent/chat/stream` - SSE 流式对话
- `POST /api/v1/agent/auto-summarize` - 自动记忆摘要
- `POST /api/v1/agent/continuity-check` - 连续性检查

### 三态修改
- `GET /api/v1/suggestions` - 建议列表
- `POST /api/v1/suggestions/{id}/action` - 确认/丢弃/应用

### 导出
- `GET /api/v1/projects/{id}/export?format=txt|markdown` - 导出小说

## 开发

```bash
# 后端测试
cd backend && python -m pytest tests/

# 前端构建
cd frontend && npm run build

# 前端开发
cd frontend && npm run dev
```

## 文档

- [产品需求文档 (PRD)](docs/PRD.md)
- [技术架构设计](docs/TECH_ARCH.md)
- [实施计划](docs/IMPLEMENTATION_PLAN.md)
- [MVP 范围定义](docs/MVP_SCOPE.md)

## License

MIT
