# AI 超长篇小说写作 Agent - 实施计划

## 文档信息
- 项目名称：AI 超长篇小说写作 Agent 应用
- 文档类型：实施计划（IMPLEMENTATION_PLAN）
- 版本：v1.0
- 状态：初版
- 创建日期：2026-03-12

---

## 1. 总体规划

### 1.1 时间线概览

| 阶段 | 时长 | 目标 | 交付物 |
|------|------|------|--------|
| **Phase 1** | 2 周 | 后端骨架 + 数据模型 | 可运行的后端 API |
| **Phase 2** | 2 周 | 前端骨架 + 基础 UI | 可访问的前端页面 |
| **Phase 3** | 2 周 | 核心对象 CRUD | 完整的对象管理功能 |
| **Phase 4** | 2 周 | 编辑器 + Agent 对话 | 可用的写作界面 |
| **Phase 5** | 2 周 | 三态机制 + 影响分析 | Suggestion 完整流程 |
| **Phase 6** | 1 周 | 记忆 + 连续性检查 | 基础智能功能 |
| **Phase 7** | 1 周 | 导出 + 测试 + 文档 | MVP 发布 |

**总计**：约 12 周

---

## 2. Phase 1：后端骨架（第 1-2 周）

### 2.1 目标
搭建后端基础架构，实现数据库模型和基础 API 框架

### 2.2 任务清单

#### Week 1

**Day 1-2：项目初始化**
- [ ] 创建后端项目结构
- [ ] 配置 pyproject.toml 和 requirements.txt
- [ ] 配置 ruff、mypy、pytest
- [ ] 创建 Docker Compose 配置

**Day 3-4：数据库模型**
- [ ] 定义所有 SQLAlchemy 模型
  - [ ] User, Project
  - [ ] Character, WorldSetting
  - [ ] Volume, Chapter, Scene
  - [ ] Suggestion, Snapshot, Memory, Dependency
- [ ] 编写 Alembic 迁移脚本
- [ ] 创建数据库初始化脚本

**Day 5：基础配置**
- [ ] 实现 config.py（环境变量管理）
- [ ] 实现 logging.py（结构化日志）
- [ ] 实现 session.py（数据库会话工厂）
- [ ] 创建 main.py（FastAPI 应用入口）

#### Week 2

**Day 1-3：Pydantic Schemas**
- [ ] 定义所有 Pydantic Schema
  - [ ] project.py, character.py, world_setting.py
  - [ ] chapter.py, scene.py
  - [ ] suggestion.py, agent.py
- [ ] 添加单元测试验证 Schema

**Day 4-5：基础 API 框架**
- [ ] 实现 deps.py（依赖注入）
- [ ] 创建 API 路由结构
- [ ] 实现健康检查端点
- [ ] 添加全局异常处理

### 2.3 验收标准
- [ ] `docker-compose up` 能启动所有服务
- [ ] 数据库迁移成功执行
- [ ] `GET /health` 返回 200
- [ ] 所有模型和 Schema 有基础测试覆盖

---

## 3. Phase 2：前端骨架（第 3-4 周）

### 3.1 目标
搭建前端基础架构，实现基础 UI 和路由

### 3.2 任务清单

#### Week 3

**Day 1-2：项目初始化**
- [ ] 创建 Next.js 项目（App Router）
- [ ] 配置 TypeScript、ESLint
- [ ] 安装依赖：TipTap, React Flow, Zustand
- [ ] 配置 Tailwind CSS

**Day 3-4：基础组件**
- [ ] 创建通用组件：Button, Input, Modal, Card
- [ ] 创建布局组件：Header, Sidebar, MainLayout
- [ ] 创建 loading 和 error 状态组件

**Day 5：状态管理**
- [ ] 配置 Zustand stores
  - [ ] projectStore.ts
  - [ ] editorStore.ts
  - [ ] agentStore.ts
- [ ] 实现 API 客户端封装

#### Week 4

**Day 1-3：路由与页面**
- [ ] 创建主要路由结构
  - [ ] `/dashboard` - 项目列表
  - [ ] `/projects/new` - 创建项目
  - [ ] `/projects/[id]` - 项目详情
  - [ ] `/projects/[id]/characters` - 人物管理
  - [ ] `/projects/[id]/worldview` - 世界观
  - [ ] `/projects/[id]/chapters` - 章节编辑
- [ ] 实现项目列表页面
- [ ] 实现创建项目页面

**Day 4-5：API 集成**
- [ ] 实现 API service 模块
  - [ ] projects.ts, characters.ts
  - [ ] chapters.ts, agents.ts
- [ ] 添加错误处理和重试逻辑
- [ ] 实现 API 认证（API Key）

### 3.3 验收标准
- [ ] 前端能成功启动并访问
- [ ] 能创建和显示项目列表
- [ ] API 调用正常工作
- [ ] 响应式布局基本正常

---

## 4. Phase 3：核心对象 CRUD（第 5-6 周）

### 4.1 目标
实现所有核心对象的完整 CRUD 功能

### 4.2 任务清单

#### Week 5：后端 CRUD

**Day 1-2：项目与人物**
- [ ] 实现 Project CRUD API
- [ ] 实现 Character CRUD API
- [ ] 添加关联查询（人物所属项目）
- [ ] 编写 API 测试

**Day 3-4：世界观与结构**
- [ ] 实现 WorldSetting CRUD API（表名：world_settings，模型：WorldSetting）
- [ ] 实现 Volume CRUD API
- [ ] 实现 Chapter CRUD API
- [ ] 实现 Scene CRUD API
- [ ] 编写 API 测试

**Day 5：快照与版本**
- [ ] 实现项目快照 API
- [ ] 实现快照回滚 API
- [ ] 编写测试

#### Week 6：前端 CRUD

**Day 1-2：表单组件**
- [ ] 创建项目表单
- [ ] 创建人物表单
- [ ] 创建世界观表单
- [ ] 表单验证

**Day 3-4：列表与详情**
- [ ] 人物列表与详情页
- [ ] 世界观列表与详情页
- [ ] 章节列表与详情页
- [ ] 场景列表

**Day 5：关联展示**
- [ ] 显示人物关系
- [ ] 显示设定引用
- [ ] 章节大纲展示

### 4.3 验收标准
- [ ] 所有核心对象可完整 CRUD
- [ ] 前后端联调通过
- [ ] 数据正确关联

---

## 5. Phase 4：编辑器与 Agent 对话（第 7-8 周）

### 5.1 目标
实现富文本编辑器和基础 Agent 对话功能

### 5.2 任务清单

#### Week 7：编辑器

**Day 1-3：TipTap 集成**
- [ ] 集成 TipTap 编辑器
- [ ] 配置基础扩展（标题、列表、格式）
- [ ] 实现内容保存逻辑
- [ ] 实现场景编辑器

**Day 4-5：章节编辑**
- [ ] 章节编辑页面布局
- [ ] 场景列表与编辑器联动
- [ ] 章节大纲编辑

#### Week 8：Agent 对话

**Day 1-3：LLM 服务**
- [ ] 实现 LLMService（统一调用接口）
- [ ] 支持多模型切换配置
- [ ] 实现流式输出
- [ ] 添加重试和错误处理

**Day 4-5：Agent 框架**
- [ ] 实现 Agent 基类
- [ ] 实现 WritingOrchestrator
- [ ] 实现基础对话 API
- [ ] 前端对话面板组件

### 5.3 验收标准
- [ ] 编辑器可正常编辑和保存
- [ ] Agent 可返回基础对话响应
- [ ] 流式输出正常工作

---

## 6. Phase 5：三态机制与影响分析（第 9-10 周）

### 6.1 目标
实现 Suggestion 三态修改机制和基础影响分析

### 6.2 任务清单

#### Week 9：三态机制

**Day 1-3：后端实现**
- [ ] Suggestion CRUD API
- [ ] 状态转换逻辑（draft → patched → committed）
- [ ] Patch 应用逻辑
- [ ] 回滚逻辑

**Day 4-5：前端实现**
- [ ] 建议列表组件
- [ ] Diff 预览组件
- [ ] 确认/丢弃操作
- [ ] 状态指示器

#### Week 10：影响分析

**Day 1-3：依赖追踪**
- [ ] Dependency 模型完善
- [ ] 实现引用追踪逻辑
- [ ] 实现影响分析算法
- [ ] 影响分析 API

**Day 4-5：Agent 集成**
- [ ] 各 Agent 生成 Suggestion
- [ ] 影响分析结果展示
- [ ] 风险等级标记

### 6.3 验收标准
- [ ] 完整的三态流程可用
- [ ] 修改后能显示影响范围
- [ ] 能正确应用和回滚修改

---

## 7. Phase 6：记忆与连续性检查（第 11 周）

### 7.1 目标
实现基础记忆抽取、检索和连续性检查

### 7.2 任务清单

**Day 1-2：记忆服务**
- [ ] 实现章节摘要生成
- [ ] 实现关键事实抽取
- [ ] 向量嵌入与存储（pgvector）
- [ ] 相似度检索 API

**Day 3-4：连续性检查**
- [ ] 设定冲突检查规则
- [ ] 人设一致性检查
- [ ] 连续性检查 API
- [ ] 问题报告格式

**Day 5：集成**
- [ ] Agent 调用记忆服务
- [ ] 检查结果展示

### 7.3 验收标准
- [ ] 能检索相关历史内容
- [ ] 能检测基础连续性问题
- [ ] 检查结果可读

---

## 8. Phase 7：导出、测试与收尾（第 12 周）

### 8.1 目标
完成导出功能，全面测试，完善文档

### 8.2 任务清单

**Day 1-2：导出功能**
- [ ] TXT 导出
- [ ] Markdown 导出
- [ ] 前端导出按钮

**Day 3-4：测试**
- [ ] 完整 E2E 测试流程
- [ ] 性能测试
- [ ] 安全检查
- [ ] Bug 修复

**Day 5：文档**
- [ ] API 文档生成
- [ ] 部署文档
- [ ] 用户使用指南

### 8.3 验收标准
- [ ] 所有核心功能可用
- [ ] 无严重 Bug
- [ ] 文档完整

---

## 9. 资源规划

### 9.1 人力配置
| 角色 | 人数 | 职责 |
|------|------|------|
| 全栈开发 | 1 | 后端 + 前端实现 |
| AI 工程师 | 0.5 | Prompt 设计、Agent 调优 |
| 测试 | 0.5 | 测试用例编写、QA |

### 9.2 基础设施
- 开发环境：本地 Docker Compose
- LLM API：OpenAI 兼容接口
- 数据库：PostgreSQL + pgvector

---

## 10. 风险管理

### 10.1 技术风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| LLM API 不稳定 | 中 | 高 | 实现重试、支持多模型 |
| pgvector 性能问题 | 低 | 中 | 监控、预留迁移方案 |
| 前端状态复杂 | 中 | 中 | 使用 Zustand、保持简洁 |

### 10.2 进度风险

| 风险 | 应对 |
|------|------|
| 某个阶段延期 | 评估是否影响 MVP，可延后非核心功能 |
| 需求变更 | 严格控制 MVP 范围，变更留待 V2 |

---

## 11. 交付物清单

### 11.1 代码交付
- [ ] 后端代码仓库
- [ ] 前端代码仓库
- [ ] Docker Compose 配置
- [ ] 数据库迁移脚本

### 11.2 文档交付
- [ ] API 文档
- [ ] 部署指南
- [ ] 用户手册
- [ ] 架构文档

### 11.3 测试交付
- [ ] 单元测试
- [ ] API 集成测试
- [ ] E2E 测试（如有）

---

## 12. 成功标准

### 12.1 MVP 发布条件
1. 所有 Must Have 功能完成
2. 通过验收标准测试
3. 无 P0/P1 级 Bug
4. 文档完整

### 12.2 后续规划
- 收集用户反馈
- V2 需求分析
- 技术债评估
