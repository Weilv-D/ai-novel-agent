# AI 超长篇小说写作 Agent - MVP 范围定义

> 归档说明：本文档用于保留历史 MVP 范围，不作为当前实现与质量基线。当前真实状态请以 `docs/README.md` 中的实现、API 与 QA 文档为准。

## 文档信息
- 项目名称：AI 超长篇小说写作 Agent 应用
- 文档类型：MVP 范围定义（MVP_SCOPE）
- 版本：v2.0
- 状态：交付基线
- 创建日期：2026-03-12
- 更新日期：2026-03-14

---

## 1. MVP 目标

**核心目标**：验证"对象级 Agent 写作系统"的核心价值，即：
1. AI 能否理解作品工程而不仅是生成文本
2. 修改传播机制是否有效
3. 三态修改机制是否给用户足够的控制感

**成功标准**：
- ✅ 用户能创建一个完整的小说项目（人物+设定+大纲+章节）
- ✅ 用户能通过对话让 AI 修改任意对象
- ✅ 修改后系统能识别影响范围
- ✅ 用户能预览、确认或回滚 AI 的修改

---

## 2. 必做功能（Must Have）

### 2.1 项目管理 ✅
- [x] 创建/编辑/删除项目
- [x] 设置作品基本信息（题材、受众、目标字数）
- [x] 项目状态标记（构思/连载/完结）
- [x] 项目快照与回滚（手动触发）

### 2.2 世界观与设定库 ✅
- [x] 创建/编辑/删除设定条目
- [x] 设定分类（魔法体系、地理、历史、规则等）
- [x] AI 对话式修改世界观（LoreAgent）
- [x] 修改后影响范围识别（Dependency 分析）

### 2.3 人物系统 ✅
- [x] 创建/编辑/删除人物
- [x] 人物档案（姓名、外貌、性格、背景等）
- [x] 人物关系网络（JSON 存储）
- [x] AI 对话式调整人设（CharacterAgent）
- [x] 修改后影响章节识别

### 2.4 故事结构 ✅
- [x] 创建/编辑/删除卷
- [x] 创建/编辑/删除章节
- [x] 章节大纲编辑
- [x] 章节排序
- [x] AI 生成章纲（OutlineAgent）

### 2.5 场景与正文 ✅
- [x] 创建/编辑/删除场景
- [x] 场景参数设置（POV 人物、地点）
- [x] AI 场景生成（DraftAgent）

### 2.6 对象级 AI 对话 ✅
- [x] 浮动对话面板（AgentChatPanel）
- [x] 基于当前对象上下文对话
- [x] SSE 流式响应
- [x] 项目/人物/章节/场景详情页集成

### 2.7 三态修改机制 ✅
- [x] Suggestion（建议）：Agent 自动生成
- [x] Patch（补丁）：用户确认后转为预览状态
- [x] Commit（提交）：应用到目标对象
- [x] Discard（丢弃）：用户拒绝
- [x] 建议列表管理（SuggestionList 组件）

### 2.8 影响分析 ✅
- [x] 引用追踪（Dependency 模型）
- [x] 修改后列出受影响对象
- [x] 风险等级标记（ImpactAnalysis 组件）

### 2.9 记忆与检索 ✅
- [x] 章节摘要自动生成（auto_summarize）
- [x] 关键事实抽取（LLM 提取 + 分类）
- [x] 向量嵌入存储（pgvector / SQLite fallback）
- [x] 语义检索（cosine similarity search）

### 2.10 连续性检查 ✅
- [x] ContinuityAgent 检查
- [x] 加载全项目上下文验证一致性
- [x] 问题报告输出（continuity_fix suggestion）

### 2.11 导出功能 ✅
- [x] 导出 TXT
- [x] 导出 Markdown
- [x] 前端导出按钮

### 2.12 认证与安全 ✅
- [x] API Key 认证（X-API-Key header）
- [x] CORS 配置

---

## 3. 不做功能（Won't Have - 留待后续版本）

### 3.1 V2 再考虑
- GraphRAG 高级检索
- TipTap 富文本编辑器集成
- React Flow 知识图谱可视化
- 复杂影响分析可视化（依赖图展示）
- 人物弧光追踪器
- 时间线视图
- 伏笔账本
- Devil's Advocate Agent

### 3.2 V3 再考虑
- 协作工作台
- 实时协同编辑
- 项目成员权限系统
- 文风克隆
- 跨媒介资产转换

### 3.3 MVP 明确不做
- 社区与分享功能
- 自动封面与插图生成
- 剧本/漫画自动改编
- 移动端优化（仅响应式设计）
- 多语言支持

---

## 4. 技术实现概览

### 4.1 后端架构
```
FastAPI + SQLAlchemy 2.0 (async)
├── 10 个数据模型（Project, Character, WorldSetting, Volume, Chapter, Scene, Suggestion, Snapshot, Memory, Dependency）
├── 70+ API 端点
├── 5 个 AI Agent（Lore, Character, Outline, Draft, Continuity）
├── WritingOrchestrator（LLM 意图分类 + 路由）
├── LLM Service（OpenAI SDK 兼容，重试，流式）
└── Export Service（TXT + Markdown）
```

### 4.2 前端架构
```
Next.js 15 (App Router) + TypeScript + Tailwind CSS
├── 21 个页面路由
├── Zustand 状态管理（projectStore, chatStore）
├── API 客户端（fetchApi + SSE streaming）
├── AgentChatPanel（浮动 AI 对话）
├── SuggestionCard/List（三态 UI）
├── DiffPreview + ImpactAnalysis
└── Export 下载
```

### 4.3 技术栈
| 组件 | 技术 | 实际版本 |
|------|------|---------|
| 前端 | Next.js | 15.5 |
| 后端 | FastAPI | 0.104+ |
| 数据库 | PostgreSQL + pgvector / SQLite（开发） | 16+ |
| 状态管理 | Zustand | 4+ |
| LLM | OpenAI SDK（兼容模式） | 1.0+ |

---

## 5. 验收标准

### 5.1 功能验收 ✅
1. ✅ **项目创建流程**：用户能创建完整项目（含设定和人物）
2. ✅ **AI 对话修改**：用户能通过对话修改不同类型对象
3. ✅ **影响分析**：修改对象后系统能识别受影响对象
4. ✅ **三态机制**：完成 建议→确认→应用 的完整流程
5. ✅ **导出**：项目能导出为 TXT 和 Markdown

### 5.2 构建验收 ✅
- ✅ 后端 Python 文件全部通过语法检查
- ✅ 前端 `next build` 21 个页面全部编译通过
- ✅ 已有 35+ 测试文件覆盖核心 CRUD

---

## 6. 技术债清单

### 6.1 已知简化
1. **认证系统**：MVP 仅实现简单 API Key，无复杂权限
2. **向量存储**：开发使用 SQLite fallback，生产需要 PostgreSQL + pgvector
3. **影响分析**：仅实现简单的引用追踪，无复杂依赖图算法
4. **记忆系统**：基础摘要和检索，无分层记忆架构
5. **富文本编辑器**：使用 textarea，未集成 TipTap
6. **SSE 流式**：基础实现，无断线重连

### 6.2 未来需改进
1. 集成 TipTap 富文本编辑器
2. 迁移至专用向量数据库（Qdrant）
3. 实现复杂影响分析算法
4. 增加 WebSocket 实时推送
5. 优化 Prompt 模板管理
6. 增加更细粒度的权限控制
7. React Flow 知识图谱可视化

---

## 7. 演进方向

1. **用户反馈收集**：核心用户试用，收集痛点
2. **性能优化**：根据实际使用情况优化
3. **V2 规划**：TipTap 编辑器 + 知识图谱 + 高级检索
4. **技术债偿还**：升级向量存储、完善认证系统
