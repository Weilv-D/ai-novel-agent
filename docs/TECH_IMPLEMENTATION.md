# 当前技术实现

最后更新：2026-03-15

## 文档定位

本文档描述仓库当前已经落地的真实实现，重点回答三类问题：

- 系统现在如何运行
- 代码按什么层次组织
- 当前交付边界在哪里

如果你要查看：

- 使用方式：见 [README.md](/home/weilv/workspace/prjforfun/ai-novel-agent/README.md)
- 开发环境：见 [DEVELOPMENT.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/DEVELOPMENT.md)
- 目标架构：见 [TECH_ARCH.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/TECH_ARCH.md)
- 演进计划：见 [IMPLEMENTATION_PLAN.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/IMPLEMENTATION_PLAN.md)
- 项目状态：见 [STATUS.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/STATUS.md)

## 系统定位

当前系统是一个独立实例运行的 Agent 化小说工作台。它不是通用协作平台，也不是只返回建议文本的聊天助手。主流程目标是：

- 用项目化数据结构承载长篇创作
- 用 Agent Workspace 承载创作与修改指令
- 用 preview-first 流程控制写入
- 用 verification gate 保障计划与落库一致
- 用 checkpoint compact flow 管理长期线程

## 运行拓扑

系统采用前后端分离的单体部署形态：

- 前端：Next.js App Router
- 后端：FastAPI + SQLAlchemy
- 数据层：PostgreSQL + pgvector
- 运行依赖：Redis
- 模型接口：OpenAI 兼容 LLM / Embedding API

请求流向：

1. 前端工作台发起 CRUD、Agent 线程消息、确认执行等请求。
2. 后端 API 路由进入 service 层。
3. service 层调用 CRUD、workflow、risk、skill、snapshot、memory、export 等实现。
4. PostgreSQL 持久化主数据与 Agent 运行数据。
5. Redis 提供运行期依赖与健康检查目标。

## 代码分层

### 后端

- `app/api/v1/`：HTTP 路由和依赖注入
- `app/services/`：业务编排与 Agent 主实现
- `app/models/`：SQLAlchemy 模型
- `app/schemas/`：Pydantic contract
- `app/core/`：配置、安全、日志
- `app/db/`：会话、初始化、迁移入口
- `app/agent_skills/`：通用 skill
- `app/agent_profiles/`：profile 覆盖

### 前端

- `frontend/app/`：页面路由
- `frontend/components/`：工作台与对象页组件
- `frontend/lib/`：类型、API client、展示元数据和 store
- `frontend/components/ui/`：基础 UI 组件

项目详情页内的 `AgentWorkspace.tsx` 是前端主工作台。

## 数据模型

### 创作对象

- `Project`
- `Character`
- `WorldSetting`
- `Volume`
- `Chapter`
- `Scene`

### Agent 工作流对象

- `AgentThread`
- `AgentMessage`
- `AgentRun`
- `AgentOperation`
- `AgentSubtask`
- `AgentThreadCheckpoint`

### 一致性与回溯对象

- `Snapshot`
- `Dependency`
- `Suggestion`

### 检索对象

- `Memory`

当前系统不维护 `User` 实体，也不为 `Project` 绑定 owner。

## Agent 工作流

当前 Agent 主流程稳定在项目级 `thread / run / operation`。

### 线程

每个项目有一个默认 `AgentThread`，它承载该项目的长期上下文。

### 消息

用户发送消息后，系统先写入 `AgentMessage`，然后进入规划流程。

### 规划

规划由 `app/services/agent_workflow.py` 驱动，主要步骤为：

1. 读取项目级 profile
2. 加载 profile-aware skill bundle
3. 装配项目上下文和焦点对象
4. 装配 checkpoint、planner window 和 retained window
5. 生成 planner 输出
6. 组装用户可见 operations 与内部 subtasks
7. 分类风险、装配 execution contract
8. 返回待确认的 `AgentRun`

### 执行

确认前，run 不会写入主对象。确认后：

1. 进入执行态
2. 为目标对象创建 snapshot
3. 复用 CRUD service 执行写入
4. 更新 operation 与 capability execution record
5. 进入 verification gate
6. 通过后标记 `completed`

## 内部执行层

当前内部角色包括：

- `planner`
- `researcher`
- `writer`
- `editor`
- `continuity`
- `executor`

这些角色已经具备：

- child unit contract
- subtask trace
- recovery boundary
- hook trace

它们仍属于 workflow 内部执行层，不是独立 child session。

## Profile 与 Skill

当前 skill 系统是项目级 profile-aware 设计。

### 已实现

- `Project.meta.agent_profile_id`
- 内置 `default`
- 内置 `xianxia_intrigue`
- `AGENT_SKILLS_DIR` profile 根目录覆盖
- 运行期可见的 profile / skill catalog

### 规范源

`xianxia_intrigue` 直接使用 `others/` 中的提示词作为规范源，并以文件化 skill 暴露给 planner 和 operation。

## Contract 设计

当前后端已经把核心运行状态稳定成显式响应字段。

### Execution Contract

- phases
- child units
- capability registry
- capability execution record

### Risk Contract

- risk policy registry
- applied policies
- run risk summary

### Verification Contract

- verification status
- verification summary
- operation execution result

### Compact Contract

- compact policy
- planner window
- retained window
- active bundle contract
- checkpoint compaction boundary

前端和测试都直接消费这些字段，不需要再从非结构化 `meta` 反推状态。

## Verification Gate

当前 verification 不是单一 hash 比对，而是多层校验。

### 已实现的校验层

- 字段级校验
- snapshot linkage 校验
- snapshot-derived semantic 校验
- content transition 校验
- domain-level semantic 校验

### 当前覆盖的业务语义

- 章节序号
- 场景序号
- 卷归属
- POV 人物归属

## Compact Flow

长线程通过 checkpoint 压缩上下文。当前 planner 有两种输入模式：

- `recent_window`
- `checkpoint_delta`

checkpoint 当前保存：

- `thread_summary`
- `recent_run_digest`
- `active_object_bundle`
- `profile_id`

compact 行为通过以下 contract 对外可见：

- `compact_policy`
- `planner_window`
- `retained_window`
- `active_bundle_contract`
- `compaction_boundary`

## 前端工作台

当前 `AgentWorkspace` 不是简单聊天框，它承担这些职责：

- 消息历史展示
- run 计划与 diff 预览
- 风险摘要与确认面板
- verification 结果展示
- subtask 与 child trace 展示
- checkpoint 与 compact contract 展示

因此它是执行工作台，而不是对话容器。

## 当前交付边界

当前范围明确排除：

- 多实例协作与组织权限
- 浏览器自动化 e2e
- 真正独立运行的 child agent session
- 面向公网的完整安全加固

这些边界由产品定位决定，不代表系统内部结构不完整。
